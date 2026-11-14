"""Offline agent contracts, with injected fixtures only; no API/DB/test benchmark."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent_runtime import OpenRouterController, AgentError, run_agent, pack_ranked_context


def row(cid="c1", text="Agile uses sprints."):
    return dict(id=cid, text=text, source_id="doc", source="doc.pdf", page=1, metadata={}, score=0.8)


def search_action(query="agile"):
    return dict(action="search", query=query, tool_call={
        "id": "call1", "type": "function",
        "function": {"name": "search", "arguments": json.dumps({"query": query})}})


class FixtureController:
    def __init__(self, actions):
        self.actions = iter(actions)
        self.calls = []
    def decide(self, question, history):
        self.calls.append({"fixture": True})
        return next(self.actions)


class FixtureRetriever:
    last_search = {"fixture": True}
    def search(self, query, *, filters, top_k):
        return [row()]


class AgentRuntimeTests(unittest.TestCase):
    def test_search_then_cited_answer(self):
        c = FixtureController([search_action(), {"action": "answer", "answer": "Sprint [c1]", "citations": ["c1"]}])
        result = run_agent("What is Agile?", c, FixtureRetriever())
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["search_count"], 1)
        self.assertEqual(result["context_ids"], ["c1"])

    def test_structured_citations_render_without_inventing_ids(self):
        c = FixtureController([search_action(), {"action": "answer", "answer": "Sprint", "citations": ["c1"]}])
        result = run_agent("q", c, FixtureRetriever())
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["raw_model_answer"], "Sprint")
        self.assertEqual(result["answer"], "Sprint [c1]")
        self.assertEqual(result["citation_rendering"], "appended_model_supplied_context_ids")

    def test_unknown_or_unlisted_citations_abstain(self):
        for answer, ids in [("Text [fake]", ["fake"]), ("Text [c1] [fake]", ["c1"])]:
            c = FixtureController([search_action(), {"action": "answer", "answer": answer, "citations": ids}])
            result = run_agent("q", c, FixtureRetriever())
            self.assertEqual(result["stop_reason"], "invalid_or_missing_citations")
            self.assertEqual(result["status"], "abstain")

    def test_real_errors_are_error_not_abstention(self):
        class Broken(FixtureRetriever):
            def search(self, *args, **kwargs):
                raise ConnectionError("sensitive provider body must not be logged")
        result = run_agent("q", FixtureController([search_action()]), Broken())
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["stage"], "retrieval")
        self.assertNotIn("sensitive", json.dumps(result))

    def test_model_abstains_after_search(self):
        c = FixtureController([search_action(), {"action": "abstain", "reason": "No quoted number"}])
        result = run_agent("q", c, FixtureRetriever())
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["stop_reason"], "model_abstained")
        self.assertEqual(result["citations"], [])

    def test_search_limit(self):
        c = FixtureController([search_action(), search_action(), search_action()])
        result = run_agent("q", c, FixtureRetriever(), max_searches=2)
        self.assertEqual(result["search_count"], 2)
        self.assertEqual(result["stop_reason"], "search_limit")

    def test_budget_dedup_best_rank_and_source(self):
        context, ids = pack_ranked_context([[row("a"), row("b")], [row("b")]], 1000)
        self.assertEqual(ids, ["a", "b"])
        self.assertIn("doc.pdf | page 1", context)
        self.assertEqual(context.count("[b |"), 1)
        self.assertEqual(pack_ranked_context([[row(text="x"*1000)]], 50), ("", []))
        with self.assertRaises(AgentError):
            pack_ranked_context([[row()], [row(text="changed")]], 1000)

    def test_controller_native_tool_and_gold_free_messages(self):
        tool_dict = search_action()["tool_call"]
        tool = NS(function=NS(name="search", arguments='{"query":"agile"}'),
                  model_dump=lambda **kw: tool_dict)
        message = NS(tool_calls=[tool], model_dump=lambda **kw: {"tool_calls": [tool_dict]})
        response = NS(id="fixture", model="fixture-model", usage=None,
                      choices=[NS(message=message, finish_reason="tool_calls")])
        requests = []
        def create(**kwargs):
            requests.append(kwargs)
            return response
        client = NS(chat=NS(completions=NS(create=create)))
        controller = OpenRouterController("fixture-model", client=client)
        history = [{"tool_call": tool_dict, "queries": ["agile"], "context": "Source text",
                    "context_ids": ["c1"], "remaining_searches": 1,
                    "gold": "DO_NOT_SEND", "expected_answer": "DO_NOT_SEND"}]
        action = controller.decide("question", history)
        self.assertEqual(action["action"], "search")
        self.assertNotIn("DO_NOT_SEND", json.dumps(requests))
        self.assertEqual(requests[0]["messages"][-1]["role"], "tool")
        self.assertEqual(requests[0]["tool_choice"], "required")

    def test_controller_api_error_is_sanitized(self):
        def create(**kwargs):
            raise TimeoutError("do not log this raw body")
        client = NS(chat=NS(completions=NS(create=create)))
        controller = OpenRouterController("fixture-model", client=client)
        with self.assertRaises(AgentError):
            controller.decide("q", [])
        self.assertNotIn("raw body", json.dumps(controller.calls))


if __name__ == "__main__":
    unittest.main()
