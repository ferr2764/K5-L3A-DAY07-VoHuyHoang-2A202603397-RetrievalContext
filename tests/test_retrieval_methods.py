"""Offline retrieval contracts. No .env, database, OpenRouter or benchmark test reads."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import (LexicalRetriever, DensePgvectorRetriever, HybridRetriever,
                           reciprocal_rank_fusion, validate_request, load_snapshot)


def chunk(cid, text, section="1.2", score=0.5):
    return dict(id=cid, text=text, source_id="doc", source="doc.pdf", page=1,
                metadata={"section": section, "language": "en", "year": 2025}, score=score)


class Stub:
    def __init__(self, rows):
        self.rows, self.calls, self.last_search = rows, [], None
    def search(self, query, *, filters=None, top_k=10):
        self.calls.append((query, filters, top_k))
        self.last_search = {"offline_fixture": True}
        return copy.deepcopy(self.rows[:top_k])


class RetrievalTests(unittest.TestCase):
    def test_lexical_filters_before_cutoff_and_fixed_idf(self):
        r = LexicalRetriever([chunk("a", "agile agile", "1.2"),
                              chunk("b", "agile development", "2.1")])
        result = r.search("agile", filters={"section": "2.1"}, top_k=1)
        self.assertEqual([x["id"] for x in result], ["b"])
        self.assertEqual(r.last_search["eligible_count"], 1)
        self.assertEqual(r.search("agile", filters={"section": "missing"}), [])
        self.assertEqual(r.search("unknownword"), [])

    def test_request_rejects_gold_filters_and_invalid_types(self):
        for filters in [{"gold_page": 1}, {"year": True}, {"section": 1}, []]:
            with self.assertRaises(ValueError):
                validate_request("q", filters, 3)
        with self.assertRaises(ValueError):
            validate_request(" ", None, 3)

    def test_rrf_uses_ranks_and_deduplicates(self):
        a, b, c = chunk("a", "a", score=999), chunk("b", "b", score=0.01), chunk("c", "c")
        rows = reciprocal_rank_fusion({"dense": [a, a, b], "lexical": [b, c]}, k=60)
        self.assertEqual(rows[0]["id"], "b")
        self.assertAlmostEqual(rows[0]["score"], 1/62 + 1/61)
        self.assertAlmostEqual(next(x for x in rows if x["id"] == "a")["score"], 1/61)
        self.assertEqual(len(rows), 3)

    def test_rrf_ties_and_conflicting_identity(self):
        rows = reciprocal_rank_fusion({"dense": [chunk("b", "b")], "lexical": [chunk("a", "a")]})
        self.assertEqual([x["id"] for x in rows], ["a", "b"])
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion({"dense": [chunk("a", "old")], "lexical": [chunk("a", "changed")]})

    def test_hybrid_propagates_filter_and_keeps_branch_trace(self):
        dense, lexical = Stub([chunk("a", "a")]), Stub([chunk("b", "b")])
        r = HybridRetriever(dense, lexical)
        result = r.search("query", filters={"section": "1.2"}, top_k=3)
        self.assertEqual(len(result), 2)
        self.assertEqual(dense.calls, [("query", {"section": "1.2"}, 10)])
        self.assertEqual(lexical.calls, dense.calls)
        self.assertIn("dense_results", r.last_search)
        with self.assertRaises(ValueError):
            r.search("q", top_k=11)

    def test_hybrid_never_silently_drops_failed_branch(self):
        class Broken(Stub):
            def search(self, *args, **kwargs):
                raise ConnectionError("offline fixture failure")
        with self.assertRaises(ConnectionError):
            HybridRetriever(Broken([]), Stub([])).search("q")

    def test_dense_validates_snapshot_and_caches_without_mutation(self):
        r = DensePgvectorRetriever.__new__(DensePgvectorRetriever)
        row = chunk("a", "agile")
        from src.retrieval import corpus_fields
        r.expected = {"a": corpus_fields(row)}
        r.backend = Stub([row])
        r.backend.model = "openai/text-embedding-3-small"
        r.cache = {}
        r.verify_snapshot = lambda: None
        first = r.search("agile")
        first[0]["text"] = "mutated by caller"
        second = r.search("agile")
        self.assertEqual(second[0]["text"], "agile")
        self.assertEqual(len(r.backend.calls), 1)
        self.assertTrue(r.last_search["cache_hit"])

    def test_frozen_real_chunks_parse_without_loading_questions(self):
        self.assertEqual(len(load_snapshot()), 162)


if __name__ == "__main__":
    unittest.main()
