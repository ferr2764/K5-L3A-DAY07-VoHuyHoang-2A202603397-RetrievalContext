"""Real tool-calling controller and bounded source-grounded agent loop."""
import copy
import hashlib
import json
import re
import time
from pathlib import Path

from src.retrieval import validate_request
from src.context_builder import build_context, model_context_records

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "src/prompts/agent_system.txt"
TOOLS = [
    {"type": "function", "function": {"name": "search", "description": "Search the fixed textbook corpus for evidence.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                    "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "finish", "description": "Answer in Vietnamese with citations supported by latest context.",
     "parameters": {"type": "object", "properties": {"answer": {"type": "string", "description": "Vietnamese answer with inline [chunk-id] citations next to factual claims. The citations list alone is NOT sufficient."},
                    "citations": {"type": "array", "items": {"type": "string"}}},
                    "required": ["answer", "citations"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "abstain", "description": "Explain insufficient evidence without guessing.",
     "parameters": {"type": "object", "properties": {"reason": {"type": "string"}},
                    "required": ["reason"], "additionalProperties": False}}},
]


class AgentError(RuntimeError):
    def __init__(self, stage, kind, status_code=None):
        super().__init__(f"{stage}: {kind}")
        self.stage, self.kind, self.status_code = stage, kind, status_code

    def record(self):
        return {"stage": self.stage, "type": self.kind, "http_status": self.status_code,
                "detail": "No fallback; provider bodies/credentials omitted."}


class OpenRouterController:
    """decide(question, history) calls a real model; injectable client is for offline tests."""
    def __init__(self, model=None, *, client=None):
        import os
        from dotenv import load_dotenv
        load_dotenv(ROOT / "starter/.env")
        self.model_name = (model or os.getenv("AGENT_MODEL") or "openai/gpt-4.1-mini").strip()
        if not self.model_name:
            raise ValueError("Agent model must not be blank")
        self.prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.settings = {"temperature": 0, "max_tokens": 800, "parallel_tool_calls": False,
                         "tool_choice": "required", "max_retries": 2, "timeout_seconds": 60}
        self.calls = []
        self._owns_client = client is None
        if client is None:
            from openai import OpenAI
            key = os.getenv("OPENROUTER_API_KEY", "").strip()
            if not key:
                raise ValueError("OPENROUTER_API_KEY missing")
            client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1",
                            timeout=60.0, max_retries=2)
        self.client = client

    def manifest(self):
        return {"model": self.model_name, "prompt_sha256": hashlib.sha256(self.prompt.encode()).hexdigest(),
                "tools_sha256": hashlib.sha256(json.dumps(TOOLS, sort_keys=True).encode()).hexdigest(),
                "generation_settings": self.settings, "provider": "OpenRouter",
                "context_transport": "latest repacked cumulative context via paired assistant/tool messages"}

    def decide(self, question, history):
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must be nonempty")
        if len(history) > 1:
            raise ValueError("Only latest cumulative evidence context is allowed")
        # Build an allowlisted request, never pass arbitrary case/benchmark dictionaries.
        messages = [{"role": "system", "content": self.prompt},
                    {"role": "user", "content": question}]
        if history:
            latest = history[0]
            tool_call = latest["tool_call"]
            if tool_call["function"]["name"] != "search":
                raise AgentError("controller", "InvalidHistoryTool")
            messages.extend([
                {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                {"role": "tool", "tool_call_id": tool_call["id"],
                 "content": json.dumps({key: latest[key] for key in
                     ("queries", "context", "context_ids", "remaining_searches")}, ensure_ascii=False)}
            ])
        tick = time.perf_counter()
        call = {"request": {"model": self.model_name, "messages": copy.deepcopy(messages),
                            "tools": copy.deepcopy(TOOLS),
                            **{k: self.settings[k] for k in ["temperature", "max_tokens", "parallel_tool_calls", "tool_choice"]}}}
        self.calls.append(call)
        try:
            response = self.client.chat.completions.create(**call["request"])
        except Exception as exc:
            error = AgentError("model", type(exc).__name__, getattr(exc, "status_code", None))
            call.update(error=error.record(), elapsed_ms=(time.perf_counter()-tick)*1000)
            raise error from None
        call.update(elapsed_ms=(time.perf_counter()-tick)*1000,
                    response_id=response.id, reported_model=response.model,
                    usage=response.usage.model_dump(mode="json") if response.usage else None)
        if not response.choices:
            raise AgentError("model_response", "NoChoices")
        choice = response.choices[0]
        message = choice.message
        call["finish_reason"] = choice.finish_reason
        call["response"] = message.model_dump(mode="json", exclude_none=True)
        if choice.finish_reason in ("length", "content_filter"):
            raise AgentError("model_response", "IncompleteOrFilteredResponse")
        if not message.tool_calls or len(message.tool_calls) != 1:
            raise AgentError("model_response", "ExpectedExactlyOneToolCall")
        tool = message.tool_calls[0]
        try:
            args = json.loads(tool.function.arguments)
        except (TypeError, json.JSONDecodeError):
            raise AgentError("model_response", "InvalidToolJSON") from None
        name = tool.function.name
        expected = {"search": {"query"}, "finish": {"answer", "citations"}, "abstain": {"reason"}}
        if name not in expected or not isinstance(args, dict) or set(args) != expected[name]:
            raise AgentError("model_response", "InvalidToolSchema")
        if name == "search":
            if not isinstance(args["query"], str) or not args["query"].strip():
                raise AgentError("model_response", "EmptySearchQuery")
            return {"action": "search", "query": args["query"], "tool_call": tool.model_dump(mode="json")}
        if name == "abstain":
            if not isinstance(args["reason"], str) or not args["reason"].strip():
                raise AgentError("model_response", "InvalidAbstention")
            return {"action": "abstain", "reason": args["reason"]}
        if (not isinstance(args["answer"], str) or not args["answer"].strip()
                or not isinstance(args["citations"], list)
                or any(not isinstance(cid, str) for cid in args["citations"])):
            raise AgentError("model_response", "InvalidAnswer")
        return {"action": "answer", **args}

    def close(self):
        if self._owns_client:
            self.client.close()


def pack_ranked_context(search_results, budget):
    """Compatibility wrapper around the auditable context builder."""
    try:
        built = build_context(search_results, budget)
    except ValueError as exc:
        raise AgentError("context", str(exc)) from None
    return built["context"], built["context_ids"]


def run_agent(question, controller, retriever, *, filters=None, top_k=10, budget=4000, max_searches=2):
    filters = validate_request(question, filters, top_k)
    if type(max_searches) is not int or max_searches < 1 or type(budget) is not int or budget < 1:
        raise ValueError("Invalid budget/search limits")
    tick = time.perf_counter()
    events, searches, history = [], [], []
    result = {"question": question, "filter": filters, "status": "error", "answer": "",
              "citations": [], "context": "", "context_ids": [], "events": events}
    try:
        for _ in range(max_searches + 1):
            action = controller.decide(question, history)
            if action["action"] == "search":
                if len(searches) == max_searches:
                    result.update(status="abstain", answer="Không đủ bằng chứng trong giới hạn truy xuất để trả lời.",
                                  stop_reason="search_limit")
                    events.append({"event": "search_limit"})
                    break
                call_tick = time.perf_counter()
                try:
                    rows = retriever.search(action["query"], filters=filters, top_k=top_k)
                except Exception as exc:
                    raise AgentError("retrieval", type(exc).__name__, getattr(exc, "status_code", None)) from None
                if len(rows) > top_k or len({row["id"] for row in rows}) != len(rows):
                    raise AgentError("retrieval", "InvalidResultCountOrIDs")
                searches.append(rows)
                selection = build_context(searches, budget)
                context, ids = selection["context"], selection["context_ids"]
                result.update(context=context, context_ids=ids, context_selection=selection)
                events.append({"event": "search", "query": action["query"], "filter": filters,
                               "tool_call": action["tool_call"], "results": rows,
                               "context": context, "context_ids": ids,
                               "context_selection": selection,
                               "elapsed_ms": (time.perf_counter()-call_tick)*1000,
                               "retriever_trace": copy.deepcopy(retriever.last_search)})
                history = [{"tool_call": action["tool_call"],
                            "queries": [e["query"] for e in events if e["event"] == "search"],
                            "context": context, "context_ids": ids,
                            "remaining_searches": max_searches-len(searches)}]
            elif action["action"] == "abstain":
                result.update(status="abstain", answer="Không đủ bằng chứng trong tài liệu để trả lời.",
                              abstention_reason=action["reason"], stop_reason="model_abstained")
                events.append({"event": "abstain", "reason": action["reason"]})
                break
            elif action["action"] == "answer":
                citations = action["citations"]
                answer = action["answer"]
                used = re.findall(r"\[([^\[\]\n]+)\]", answer)
                context_valid = (bool(searches and citations) and len(citations) == len(set(citations))
                                 and all(cid in result["context_ids"] for cid in citations))
                # Tool calling returns structured citations. If the model supplies
                # valid IDs separately but no inline markers, render those exact
                # IDs visibly; never invent an ID or silently correct a wrong ID.
                if context_valid and not used:
                    result["raw_model_answer"] = answer
                    answer = answer.rstrip() + " " + " ".join(f"[{cid}]" for cid in citations)
                    result["citation_rendering"] = "appended_model_supplied_context_ids"
                    used = citations
                valid = context_valid and set(used) == set(citations)
                if not valid:
                    result.update(status="abstain", answer="Không đủ bằng chứng có citation hợp lệ để trả lời.",
                                  stop_reason="invalid_or_missing_citations", rejected_answer=action["answer"])
                    events.append({"event": "invalid_or_missing_citations"})
                else:
                    result.update(status="answered", answer=answer, citations=citations,
                                  stop_reason="model_answered")
                    events.append({"event": "answer"})
                break
            else:
                raise AgentError("controller", "UnknownAction")
        else:
            result.update(status="abstain", answer="Không đủ bằng chứng trong giới hạn xử lý để trả lời.",
                          stop_reason="decision_limit")
    except Exception as exc:
        error = exc if isinstance(exc, AgentError) else AgentError("agent", type(exc).__name__)
        result.update(status="error", error=error.record(), stop_reason="error")
        events.append({"event": "error", **error.record()})
    result.update(elapsed_seconds=time.perf_counter()-tick, search_count=len(searches),
                  model_calls=copy.deepcopy(controller.calls), model_call_count=len(controller.calls),
                  context_chars=len(result["context"]), semantic_citation_support="requires_content_review")
    sent = model_context_records(controller.calls)
    result["model_context_requests"] = sent
    result["model_context"] = sent[-1]["context"] if sent else ""
    result["model_context_ids"] = sent[-1]["context_ids"] if sent else []
    result["context_transmission"] = sent[-1]["transmission"] if sent else "not_sent"
    result["planned_context_matches_last_model_request"] = (
        sent[-1]["context"] == result["context"] if sent else None)
    usages = [call.get("usage") for call in controller.calls]
    result["usage"] = {
        "prompt_tokens": sum(u.get("prompt_tokens", 0) for u in usages if u) if usages and all(usages) else None,
        "completion_tokens": sum(u.get("completion_tokens", 0) for u in usages if u) if usages and all(usages) else None,
        "model_cost_usd": sum(u["cost"] for u in usages) if usages and all(u and isinstance(u.get("cost"), (float, int)) for u in usages) else None,
        "retrieval_embedding_cost_usd": None,
        "note": "Model usage retained per call; embedding cost unknown with current adapter. No price estimate or mock fallback."}
    return result
