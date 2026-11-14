"""Dev-only lexical context-budget diagnostics; no LLM/embedding/API calls."""
import argparse
import hashlib
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import load_snapshot, LexicalRetriever
from src.context_builder import build_context


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Fresh output directory")
    args = parser.parse_args()
    protocol_path = ROOT / "data/benchmark/evaluation_protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    path = ROOT / protocol["inputs"]["questions_path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != protocol["inputs"]["questions_sha256"]:
        raise ValueError("Benchmark checksum differs from protocol")
    # Gold stays inside this evaluator; retriever/builder receive only runtime inputs.
    questions = [q for q in json.loads(path.read_text(encoding="utf-8"))
                 if q["split"] == "dev" and q["answerable"]]
    assert len(questions) == 15
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = args.output or ROOT / "artifacts/context_dev" / stamp
    out.mkdir(parents=True, exist_ok=False)
    retriever = LexicalRetriever(load_snapshot())
    budgets = [800, 4000, 6000]
    records = []
    for q in questions:
        hits = retriever.search(q["question"], filters=q.get("filter"), top_k=10)
        for budget in budgets:
            built = build_context([hits], budget)
            valid_ids = {h["id"] for h in hits if any(
                h["source_id"] == g["source_id"] and h["page"] == g["page"]
                and norm(g["evidence"]) in norm(h["text"]) for g in q["gold"])}
            hit3 = any(h["id"] in valid_ids for h in hits[:3])
            context_hit = bool(valid_ids.intersection(built["context_ids"]))
            records.append({"query_id": q["id"], "split": "dev", "method": "tfidf",
                            "budget_chars": budget, "question": q["question"], "filter": q.get("filter"),
                            "results": hits, "hit_at_3_literal": hit3,
                            "context_evidence_literal": context_hit,
                            "valid_evidence_candidate_ids": sorted(valid_ids),
                            "context_selection": built})
    summary = []
    for budget in budgets:
        rows = [r for r in records if r["budget_chars"] == budget]
        n = sum(r["context_evidence_literal"] for r in rows)
        summary.append({"budget_chars": budget, "answerable_dev_n": len(rows),
                        "literal_context_evidence_n": n, "literal_context_evidence_rate": n/len(rows),
                        "literal_hit3_n": sum(r["hit_at_3_literal"] for r in rows),
                        "mean_context_chars": sum(r["context_selection"]["context_chars"] for r in rows)/len(rows),
                        "empty_context_n": sum(not r["context_selection"]["context_ids"] for r in rows),
                        "skipped_chunks_total": sum(r["context_selection"]["skipped_count"] for r in rows)})
    for name, value in [("traces.json", records), ("summary.json", {
        "scope": "15 dev answerable cases only; fixed TF-IDF rankings; context-budget diagnostic, not agent quality or configuration selection",
        "budgets": summary, "service_cost_usd": 0, "llm_calls": 0, "test_cases_evaluated": 0,
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "benchmark_sha256": protocol["inputs"]["questions_sha256"],
        "review_note": "Literal source/page/evidence check; no human context grades inferred."})]:
        (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved dev-only context diagnostics: {out}")


if __name__ == "__main__":
    main()
