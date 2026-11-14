"""Run baseline and dev-selected configuration on TEST only, after immutable freeze."""
import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_dev_benchmark import execute_profile,write
from src.agent_runtime import OpenRouterController
from src.retrieval import load_snapshot
from src.dev_evaluation import summarize


def main():
    if hasattr(sys.stdout,"reconfigure"):sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze",type=Path,required=True)
    args=parser.parse_args()
    frozen=json.loads(args.freeze.read_text(encoding="utf-8"))
    for path,value in frozen["file_hashes"].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=value:
            raise ValueError("Frozen input/code changed: "+path)
    controller=OpenRouterController(frozen["controller"]["model"])
    try:
        if controller.manifest()!=frozen["controller"]:
            raise ValueError("Frozen model/prompt/settings differ")
    finally:controller.close()
    profiles=[frozen["baseline"],frozen["selected"]]
    if profiles[0]["id"]==profiles[1]["id"]:profiles=profiles[:1]
    cases=[q for q in json.loads((ROOT/"data/benchmark/questions.json").read_text(encoding="utf-8"))
           if q["split"]=="test"]
    assert len(cases)==7 and sum(c["answerable"] for c in cases)==5
    chunks=load_snapshot()
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out=ROOT/"artifacts/test_benchmark"/stamp
    out.mkdir(parents=True,exist_ok=False)
    write(out/"run_manifest.json",{"scope":"TEST only; baseline and dev-selected frozen profile",
        "started_at_utc":stamp,"freeze_path":str(args.freeze),"freeze_sha256":hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        "freeze":frozen,"profiles":profiles,"test_cases":7,"answerable_cases":5,"unanswerable_cases":2,
        "latency_note":"Two profiles run concurrently; not isolated timing.",
        "no_test_tuning":True})
    rows,failures=[],[]
    tick=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(execute_profile,p,cases,chunks,frozen["controller"]["model"],out):p["id"] for p in profiles}
        for future in concurrent.futures.as_completed(futures):
            try:rows.extend(future.result())
            except Exception as exc:
                failures.append({"profile":futures[future],"error_type":type(exc).__name__,
                                 "detail":"Interrupted; per-case checkpoints retained, no fallback."})
                write(out/"profile_failures.json",failures)
    summaries=[summarize(rows,p["id"]) for p in profiles if any(r["profile"]==p["id"] for r in rows)]
    assert all(r["evaluation"]["split"]=="test" for r in rows)
    write(out/"summary.json",{"split":"test","profiles":summaries,"case_runs":len(rows),
        "expected_case_runs":7*len(profiles),"profile_failures":failures,
        "case_errors":sum(r["agent"]["status"]=="error" for r in rows),
        "status":"partial" if len(rows)!=7*len(profiles) or failures else
                 "completed_with_case_errors" if any(r["agent"]["status"]=="error" for r in rows) else "complete",
        "known_cost_subtotal_usd":sum(m["known_cost_subtotal_usd"] for m in summaries),
        "total_cost_usd":sum(m["total_cost_usd"] for m in summaries)
             if summaries and all(m["total_cost_usd"] is not None for m in summaries) else None,
        "elapsed_wall_seconds":time.perf_counter()-tick,"manual_reviews":"pending task 10",
        "freeze_unchanged":hashlib.sha256(args.freeze.read_bytes()).hexdigest()==json.loads((out/"run_manifest.json").read_text(encoding="utf-8"))["freeze_sha256"]})
    print("TEST output:",out,flush=True)
    return 0 if len(rows)==7*len(profiles) and not failures else 1


if __name__=="__main__":sys.exit(main())
