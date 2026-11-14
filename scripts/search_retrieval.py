"""One explicit retrieval call; no benchmark gold, scoring or agent execution."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval import build_retriever


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=["dense", "lexical", "hybrid"], required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--section")
    parser.add_argument("--language")
    parser.add_argument("--year", type=int)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Output exists; choose a fresh file")
    filters = {key: getattr(args, key) for key in ["section", "language", "year"]
               if getattr(args, key) is not None}
    retriever = build_retriever(args.method)
    try:
        results = retriever.search(args.query, filters=filters, top_k=args.top_k)
        data = {"query": args.query, "method": args.method, "filter": filters,
                "results": results, "top3": results[:3], "trace": retriever.last_search}
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Saved retrieval output: {args.output}")
        else:
            print(text)
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
