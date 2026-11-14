"""Explicit real agent run for one supplied question, never a benchmark batch."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent_runtime import OpenRouterController, AgentError, run_agent
from src.retrieval import build_retriever


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--profile", choices=["dense_4000", "lexical_4000", "hybrid_4000", "hybrid_6000"], default="dense_4000")
    parser.add_argument("--model", help="Override AGENT_MODEL; default openai/gpt-4.1-mini")
    parser.add_argument("--section")
    parser.add_argument("--language")
    parser.add_argument("--year", type=int)
    parser.add_argument("--output", type=Path, help="Fresh run directory, not an existing file/directory")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = args.output or ROOT / "artifacts/agent_runs" / stamp
    out.mkdir(parents=True, exist_ok=False)
    write = lambda name, obj: (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    controller = retriever = None
    try:
        path = ROOT / "data/benchmark/evaluation_protocol.json"
        protocol = json.loads(path.read_text(encoding="utf-8"))
        for key in ("questions", "chunks"):
            p = ROOT / protocol["inputs"][key+"_path"]
            if hashlib.sha256(p.read_bytes()).hexdigest() != protocol["inputs"][key+"_sha256"]:
                raise ValueError("Frozen input checksum mismatch")
        profile = next(p for p in protocol["profiles"] if p["id"] == args.profile)
        controller = OpenRouterController(args.model)
        filters = {key: getattr(args, key) for key in ("section", "language", "year") if getattr(args, key) is not None}
        write("run_manifest.json", {"scope": "single explicit query; no benchmark scoring or configuration selection",
              "started_at_utc": stamp, "profile": profile, "filter": filters,
              "protocol_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "inputs": protocol["inputs"], "controller": controller.manifest()})
        method = {"dense": "dense", "tfidf": "lexical", "hybrid_rrf": "hybrid"}[profile["method"]]
        retriever = build_retriever(method)
        result = run_agent(args.question, controller, retriever, filters=filters,
                           top_k=profile["return_top_k"], budget=profile["context_budget_chars"],
                           max_searches=profile["max_searches"])
        result["query_id"] = "single-query"
        write("trace.json", result)
        (out / "context.txt").write_text(result["context"], encoding="utf-8")
        (out / "model_context.txt").write_text(result["model_context"], encoding="utf-8")
        write("context_selection.json", result.get("context_selection", {
            "context": "", "context_ids": [], "note": "No retrieval context was constructed."}))
        if result["status"] == "error":
            print(f'Agent failed ({result["error"]["stage"]}: {result["error"]["type"]}); trace: {out}')
            return 1
        print(result["answer"])
        print(f'Status: {result["status"]}; searches: {result["search_count"]}; trace: {out}')
        return 0
    except Exception as exc:
        error = exc.record() if isinstance(exc, AgentError) else {"stage": "setup", "type": type(exc).__name__,
                  "http_status": getattr(exc, "status_code", None), "detail": "No fallback; secret/provider body omitted."}
        write("cli_error.json" if (out / "trace.json").exists() else "trace.json",
              {"status": "error", "error": error,
               "model_calls": controller.calls if controller else []})
        print(f'Agent failed ({error["stage"]}: {error["type"]}); trace: {out}')
        return 1
    finally:
        if retriever is not None:
            retriever.close()
        if controller is not None:
            controller.close()


if __name__ == "__main__":
    sys.exit(main())
