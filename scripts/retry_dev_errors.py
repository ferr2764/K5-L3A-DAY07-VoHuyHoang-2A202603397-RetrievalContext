"""Retry only failed cases from a saved DEV run, retaining original attempts and costs."""
import concurrent.futures
import copy
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_dev_benchmark import execute_profile, write
from src.agent_runtime import OpenRouterController
from src.retrieval import load_snapshot
from src.dev_evaluation import summarize, usage_totals

ORIGINAL = ROOT / "artifacts/dev_benchmark/20261114T092856910861Z"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    manifest = json.loads((ORIGINAL / "run_manifest.json").read_text(encoding="utf-8"))
    protocol_path = ROOT / "data/benchmark/evaluation_protocol.json"
    assert hashlib.sha256(protocol_path.read_bytes()).hexdigest() == manifest["protocol_sha256"]
    inputs = manifest["inputs"]
    qpath = ROOT / inputs["questions_path"]
    assert hashlib.sha256(qpath.read_bytes()).hexdigest() == inputs["questions_sha256"]
    cases = {q["id"]: q for q in json.loads(qpath.read_text(encoding="utf-8")) if q["split"] == "dev"}
    original_rows = []
    for profile in manifest["profiles"]:
        original_rows.extend(json.loads((ORIGINAL / profile["id"] / "records.json").read_text(encoding="utf-8")))
    assert len(original_rows) == 68
    failed = [r for r in original_rows if r["agent"]["status"] == "error"]
    assert len(failed) == 19
    controller = OpenRouterController(manifest["controller"]["model"])
    try:
        assert controller.manifest() == manifest["controller"], "Model/prompt/tools/settings changed"
    finally:
        controller.close()
    chunks = load_snapshot()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "artifacts/dev_retries" / stamp
    out.mkdir(parents=True, exist_ok=False)
    write(out / "run_manifest.json", {
        "scope": "Retry the 19 original DEV errors exactly once after student restored credit/limit.",
        "original_run": ORIGINAL.relative_to(ROOT).as_posix(), "original_manifest": manifest,
        "retry_policy": "Original successful cases never rerun; use latest retry outcome, not best answer. Keep all original errors/costs. No test.",
        "requested_cases": [{"profile": r["profile"], "query_id": r["query_id"]} for r in failed],
        "model_prompt_tools_settings_verified_unchanged": True,
        "cache_note": "Retry starts new per-profile caches; original-query call is repeated for instrumentation, but original ranking retained in merged comparison."})
    retried = []
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = []
        for profile in manifest["profiles"]:
            selected = [cases[r["query_id"]] for r in failed if r["profile"] == profile["id"]]
            if selected:
                futures.append(pool.submit(execute_profile, profile, selected, chunks,
                                           manifest["controller"]["model"], out))
        for future in concurrent.futures.as_completed(futures):
            retried.extend(future.result())
    assert len(retried) == 19
    lookup = {(r["profile"], r["query_id"]): r for r in retried}
    effective = []
    for old in original_rows:
        key = old["profile"], old["query_id"]
        if key in lookup:
            row = copy.deepcopy(lookup[key])
            row["original_attempt_status"] = old["agent"]["status"]
            row["ranking_source"] = "original_run"
            row["retry_ranking_ids_match_original"] = (
                [h["id"] for h in old["raw"]["results"]] ==
                [h["id"] for h in row["raw"]["results"]])
            row["raw"] = old["raw"]
            for name in ["raw_hit_at_1_literal", "raw_hit_at_3_literal"]:
                row["evaluation"][name] = old["evaluation"][name]
            effective.append(row)
        else:
            effective.append(copy.deepcopy(old))
    profiles = [summarize(effective, p["id"]) for p in manifest["profiles"]]
    billing = []
    for profile in manifest["profiles"]:
        name = profile["id"]
        all_attempts = [r for r in original_rows + retried if r["profile"] == name]
        models = usage_totals([c for r in all_attempts for c in r["agent"].get("model_calls", [])])
        embeddings = usage_totals([e for r in all_attempts for e in r["embedding_requests"]])
        billing.append({"profile": name, "attempts_including_original_and_retry": len(all_attempts),
                        "model_usage_all_attempts": models, "embedding_usage_all_attempts": embeddings,
                        "known_cost_subtotal_usd_all_attempts": models["known_cost_usd"]+embeddings["known_cost_usd"],
                        "total_cost_usd_all_attempts": models["cost_usd"]+embeddings["cost_usd"]
                          if models["cost_usd"] is not None and embeddings["cost_usd"] is not None else None})
    error_count = sum(r["agent"]["status"] == "error" for r in effective)
    write(out / "effective_records.json", effective)
    write(out / "summary.json", {
        "scope": "Original successful cases plus exactly one new attempt per failed dev case.",
        "profiles": profiles, "billing_all_attempts": billing,
        "effective_case_runs": len(effective), "retry_attempts": len(retried),
        "effective_agent_errors": error_count, "test_cases_evaluated": 0,
        "status": "complete" if error_count == 0 else "completed_with_case_errors",
        "elapsed_retry_wall_seconds": time.perf_counter()-start,
        "known_cost_subtotal_usd_all_attempts": sum(b["known_cost_subtotal_usd_all_attempts"] for b in billing),
        "cost_note": "Original failed requests with no usage remain unknown, not assumed free; effective profile costs exclude superseded attempts. Billing section includes every attempt.",
        "manual_semantic_review": "pending; no winner selected"})
    print(f"Retry results: {out}; remaining errors: {error_count}", flush=True)
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
