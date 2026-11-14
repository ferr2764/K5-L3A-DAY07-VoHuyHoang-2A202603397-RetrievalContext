"""Run the four predeclared profiles on DEV only; real APIs, checkpoint every case."""
import argparse
import concurrent.futures
import copy
import hashlib
import importlib.metadata
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent_runtime import OpenRouterController, AgentError, run_agent
from src.context_builder import build_context
from src.retrieval import load_snapshot, LexicalRetriever, HybridRetriever
from src.dev_evaluation import MeasuredDenseRetriever, evaluate_case, summarize


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def execute_profile(profile, cases, chunks, model, out):
    lexical = LexicalRetriever(chunks)
    dense = None
    directory = out / profile["id"]
    directory.mkdir()
    records = []
    lookup = {c["id"]: c for c in chunks}
    try:
        if profile["method"] != "tfidf":
            dense = MeasuredDenseRetriever(chunks)
        retriever = (lexical if profile["method"] == "tfidf" else dense
                     if profile["method"] == "dense" else HybridRetriever(dense, lexical))
        for case in cases:
            case_dir = directory / case["id"]
            case_dir.mkdir()
            before = len(dense.embedding_requests) if dense else 0
            controller = OpenRouterController(model)
            try:
                tick = time.perf_counter()
                raw = {"query": case["question"], "filter": case.get("filter")}
                try:
                    # Independent original-query ranking, no gold passed.
                    hits = retriever.search(case["question"], filters=case.get("filter"),
                                            top_k=profile["return_top_k"])
                    raw.update(results=hits, top3=hits[:3], trace=copy.deepcopy(retriever.last_search),
                               context_selection=build_context([hits], profile["context_budget_chars"]))
                except Exception as exc:
                    hits = []
                    raw.update(results=[], top3=[], error={"type": type(exc).__name__,
                        "http_status": getattr(exc, "status_code", None), "detail": "No fallback"})
                raw["elapsed_ms"] = (time.perf_counter()-tick)*1000
                # Full case stays in evaluator. Only these runtime inputs reach agent.
                agent = run_agent(case["question"], controller, retriever, filters=case.get("filter"),
                    top_k=profile["return_top_k"], budget=profile["context_budget_chars"],
                    max_searches=profile["max_searches"])
                agent["query_id"] = case["id"]
                evaluation = evaluate_case(case, hits, agent, lookup)
                embedding_events = copy.deepcopy(dense.embedding_requests[before:]) if dense else []
                record = {"profile": profile["id"], "query_id": case["id"], "raw": raw,
                          "agent": agent, "evaluation": evaluation, "embedding_requests": embedding_events}
                write(case_dir / "original_query.json", raw)
                write(case_dir / "agent_trace.json", agent)
                write(case_dir / "evaluation.json", evaluation)
                write(case_dir / "embedding_usage.json", embedding_events)
                write(case_dir / "context_selection.json", agent.get("context_selection", {}))
                (case_dir / "context.txt").write_text(agent.get("context", ""), encoding="utf-8")
                (case_dir / "model_context.txt").write_text(agent.get("model_context", ""), encoding="utf-8")
                records.append(record)
                write(directory / "summary.json", summarize(records, profile["id"]))
                print(f'{profile["id"]} {case["id"]}: {agent["status"]}; searches={agent["search_count"]}', flush=True)
            finally:
                controller.close()
        write(directory / "records.json", records)
        return records
    finally:
        if dense is not None:
            dense.close()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="One shared model for every profile")
    parser.add_argument("--workers", type=int, choices=[1,2,3,4], default=4)
    args = parser.parse_args()
    path = ROOT / "data/benchmark/evaluation_protocol.json"
    protocol = json.loads(path.read_text(encoding="utf-8"))
    qpath = ROOT / protocol["inputs"]["questions_path"]
    if hashlib.sha256(qpath.read_bytes()).hexdigest() != protocol["inputs"]["questions_sha256"]:
        raise ValueError("Benchmark checksum mismatch")
    # Only dev cases are evaluated; no test gold enters evaluator loops or runtime.
    cases = [q for q in json.loads(qpath.read_text(encoding="utf-8")) if q["split"] == "dev"]
    assert len(cases)==17 and sum(q["answerable"] for q in cases)==15
    chunks = load_snapshot()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "artifacts/dev_benchmark" / stamp
    out.mkdir(parents=True, exist_ok=False)
    controller = OpenRouterController(args.model)
    try:
        model = controller.model_name
        write(out / "run_manifest.json", {"scope": "DEV only: 17 cases x 4 predeclared profiles; no test",
              "started_at_utc": stamp, "controller": controller.manifest(),
              "protocol_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "profiles": protocol["profiles"], "inputs": protocol["inputs"], "workers": args.workers,
              "versions": {name: importlib.metadata.version(name) for name in ["openai","psycopg","python-dotenv"]},
              "cache_policy": "Independent dense instance per profile, cache within profile; original query runs before agent; cache hits disclosed; no cross-profile reuse.",
              "latency_note": "Profiles may run concurrently; single observation, not isolated latency benchmarking.",
              "grading": "literal retrieval/context only; semantic answer/citation/abstention grades pending",
              "selected_configuration": None})
    finally:
        controller.close()
    records, failures = [], []
    tick = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(execute_profile, p, cases, chunks, model, out): p["id"] for p in protocol["profiles"]}
        for future in concurrent.futures.as_completed(futures):
            try:
                records.extend(future.result())
            except Exception as exc:
                failure = {"profile": futures[future], "type": type(exc).__name__,
                           "detail": "Profile interrupted; completed per-case artifacts retained. No fallback."}
                failures.append(failure)
                write(out / "profile_failures.json", failures)
    summaries = [summarize(records, p["id"]) for p in protocol["profiles"]
                 if any(r["profile"]==p["id"] for r in records)]
    write(out / "summary.json", {"split": "dev", "profiles": summaries, "profile_failures": failures,
          "completed_case_runs": len(records), "expected_case_runs": 68,
          "elapsed_wall_seconds": time.perf_counter()-tick,
          "total_cost_usd": sum(s["total_cost_usd"] for s in summaries)
              if summaries and all(s["total_cost_usd"] is not None for s in summaries) else None,
          "known_cost_subtotal_usd": sum(s["known_cost_subtotal_usd"] for s in summaries),
          "test_cases_evaluated": 0, "status": ("partial" if len(records)!=68 or failures else "completed_with_case_errors" if any(r["agent"]["status"]=="error" for r in records) else "complete"),
          "manual_review": "pending; no configuration selected"})
    print(f'Dev run saved: {out}', flush=True)
    return 0 if len(records)==68 and not failures else 1


if __name__ == "__main__":
    sys.exit(main())
