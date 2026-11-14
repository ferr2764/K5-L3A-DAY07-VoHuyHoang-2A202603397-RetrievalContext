"""Explicit paid integration smoke check; never imported by offline test discovery."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import load_snapshot, LexicalRetriever, DensePgvectorRetriever, HybridRetriever


def main():
    chunks = load_snapshot()
    dense = None
    try:
        dense = DensePgvectorRetriever(chunks)
        lexical = LexicalRetriever(chunks)
        hybrid = HybridRetriever(dense, lexical)
        query = "Agile chia dự án thành những đơn vị nào?"
        filters = {"section": "1.2"}
        observations = []
        for name, retriever in [("dense", dense), ("lexical", lexical), ("hybrid", hybrid)]:
            results = retriever.search(query, filters=filters, top_k=10)
            assert all(h["metadata"]["section"] == "1.2" for h in results)
            assert len({h["id"] for h in results}) == len(results)
            observations.append({"method": name, "results": results, "trace": retriever.last_search})
            print(name, "returned", len(results), "top3 pages:", [h["page"] for h in results[:3]])
        assert hybrid.last_search["dense_call"]["cache_hit"]
        path = ROOT / "artifacts/retrieval_smoke.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({
            "scope": "Integration smoke check only, using previously shown Agile query; no benchmark quality metrics or test data.",
            "query": query, "filter": filters,
            "cost_note": "One real query-embedding request through dense; hybrid reuses its ranked-result cache. Actual USD unknown.",
            "methods": observations}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Integration smoke check passed; saved artifacts/retrieval_smoke.json")
    finally:
        if dense is not None:
            dense.close()


if __name__ == "__main__":
    main()
