"""Context invariants and serialized model-payload checks, offline only."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.context_builder import build_context, model_context_records
from src.agent_runtime import run_agent
from tests.test_agent_runtime import FixtureController, FixtureRetriever, search_action


def row(cid, text, page=7):
    return dict(id=cid, text=text, source_id="doc", source="book.pdf",
                page=page, metadata={"section": "2.1"}, score=0.9)


class ContextBuilderTests(unittest.TestCase):
    def test_dedup_repack_and_preserve_exact_text(self):
        a, b = row("a", "Only if condition X.\nExcept case Y."), row("b", "Complete statement.")
        built = build_context([[a, b], [b, a]], 1000)
        self.assertEqual(built["duplicates_removed"], 2)
        self.assertEqual(built["context_ids"], ["a", "b"])
        self.assertIn(a["text"], built["context"])
        self.assertIn("[a | book.pdf | page 7]", built["context"])

    def test_budget_counts_header_separator_and_unicode(self):
        a, b = row("a", "Điều kiện"), row("b", "Ngắn")
        one = build_context([[a]], 1000)
        exact = build_context([[a,b]], one["context_chars"])
        self.assertEqual(exact["context_ids"], ["a"])
        self.assertEqual(exact["context_chars"], one["context_chars"])
        self.assertEqual(exact["decisions"][1]["reason"], "insufficient_remaining_budget")
        self.assertEqual(exact["remaining_chars"], 0)

    def test_skip_oversized_then_continue_and_never_truncate(self):
        a, b = row("a", "X"*1000), row("b", "Short")
        built = build_context([[a,b]], 80)
        self.assertEqual(built["context_ids"], ["b"])
        self.assertEqual(built["decisions"][0]["reason"], "block_exceeds_total_budget")
        self.assertNotIn("XXX", built["context"])

    def test_later_high_rank_replaces_low_rank_evidence_under_budget(self):
        a, b = row("z", "A"*20), row("a", "B"*20)
        before = build_context([[a,b]], 80)
        built = build_context([[a,b], [b]], 80)
        self.assertEqual(before["context_ids"], ["z"])
        self.assertEqual(built["context_ids"], ["a"])
        self.assertEqual(built["decisions"][0]["best_reciprocal_rank"], 1/61)

    def test_same_id_different_source_is_error(self):
        with self.assertRaises(ValueError):
            build_context([[row("a","text")], [row("a","text",page=8)]], 1000)

    def test_exact_model_context_extraction(self):
        payload = {"context": "[c1 | book.pdf | page 7]\ntext", "context_ids": ["c1"]}
        calls = [{"request": {"messages": [{"role": "tool", "content": json.dumps(payload)}]},
                  "response_id": "real-or-fixture-id"}]
        record = model_context_records(calls)[0]
        self.assertEqual(record["context"], payload["context"])
        self.assertEqual(record["context_sha256"], hashlib.sha256(payload["context"].encode()).hexdigest())
        self.assertEqual(record["transmission"], "response_received")

    def test_agent_saves_selection_reasons(self):
        controller = FixtureController([search_action(), {"action":"answer","answer":"Sprint [c1]","citations":["c1"]}])
        result = run_agent("q", controller, FixtureRetriever())
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["context_selection"]["context"], result["context"])
        self.assertEqual(result["events"][0]["context_selection"]["selected_count"], 1)
        self.assertEqual(result["context_transmission"], "not_sent")


if __name__ == "__main__":
    unittest.main()
