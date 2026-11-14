"""Dev evaluator and transparent embedding usage instrumentation; no judge model."""
import copy
import math
import time
import unicodedata
from types import SimpleNamespace

from src.retrieval import DensePgvectorRetriever


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


class MeasuredDenseRetriever(DensePgvectorRetriever):
    """Same dense algorithm; record usage returned by real embedding calls."""
    def __init__(self, chunks):
        super().__init__(chunks)
        self.embedding_requests = []
        real_client = self.backend.client
        real_create = real_client.embeddings.create
        def measured_create(**kwargs):
            tick = time.perf_counter()
            try:
                response = real_create(**kwargs)
            except Exception as exc:
                self.embedding_requests.append({"status": "error", "type": type(exc).__name__,
                    "http_status": getattr(exc, "status_code", None),
                    "elapsed_ms": (time.perf_counter()-tick)*1000, "usage": None})
                raise
            self.embedding_requests.append({"status": "ok", "id": getattr(response, "id", None),
                "elapsed_ms": (time.perf_counter()-tick)*1000,
                "usage": response.usage.model_dump(mode="json") if response.usage else None})
            return response
        self.backend.client = SimpleNamespace(
            embeddings=SimpleNamespace(create=measured_create), close=real_client.close)

    def search(self, query, *, filters=None, top_k=10):
        before = len(self.embedding_requests)
        rows = super().search(query, filters=filters, top_k=top_k)
        events = copy.deepcopy(self.embedding_requests[before:])
        self.last_search["embedding_requests"] = events
        self.last_search["measured_embedding_cost"] = usage_totals(events)
        return rows


def usage_totals(events):
    costs = []
    prompt_tokens = []
    unknown = 0
    for event in events:
        usage = event.get("usage") or {}
        value = usage.get("cost")
        if type(value) in (int, float) and math.isfinite(value):
            costs.append(value)
        else:
            unknown += 1
        token = usage.get("prompt_tokens", usage.get("total_tokens"))
        if type(token) is int:
            prompt_tokens.append(token)
    return {"request_count": len(events), "known_cost_usd": sum(costs),
            "cost_usd": sum(costs) if unknown == 0 else None,
            "unknown_cost_request_count": unknown, "prompt_tokens_known": sum(prompt_tokens)}


def evaluate_case(case, raw_hits, agent, chunks_by_id):
    # Only the evaluator accesses gold. Retrievers/controllers never receive case.
    def valid(chunk):
        return any(chunk["source_id"] == g["source_id"] and chunk["page"] == g["page"]
                   and norm(g["evidence"]) in norm(chunk["text"]) for g in case.get("gold", []))
    answerable = case["answerable"]
    flags = [valid(h) for h in raw_hits[:3]] if answerable else []
    final_context = agent.get("model_context", "")
    context_ids = agent.get("model_context_ids", [])
    context_hit = False
    if answerable and agent["status"] != "error":
        context_hit = any(cid in chunks_by_id and valid(chunks_by_id[cid])
                          and norm(chunks_by_id[cid]["text"]) in norm(final_context)
                          for cid in context_ids)
    return {"query_id": case["id"], "split": case.get("split", "dev"), "answerable": answerable,
            "raw_hit_at_1_literal": bool(flags and flags[0]) if answerable else None,
            "raw_hit_at_3_literal": any(flags) if answerable else None,
            "final_model_context_evidence_literal": context_hit if answerable else None,
            "status": agent["status"], "search_count": agent.get("search_count", 0),
            "model_call_count": agent.get("model_call_count", 0),
            "manual_review": {"grounded_answer_0_2": None, "context_0_2": None,
                              "citation_support": [None for _ in agent.get("citations", [])],
                              "abstention_correct": None, "reason": None},
            "scoring": "literal source/page/complete-evidence; equivalence/content grading pending"}


def summarize(records, profile):
    import statistics
    rows = [r for r in records if r["profile"] == profile]
    answerable = [r for r in rows if r["evaluation"]["answerable"]]
    successful = [r for r in rows if r["agent"]["status"] != "error"]
    count = lambda key: sum(bool(r["evaluation"][key]) for r in answerable)
    models = [call for r in rows for call in r["agent"].get("model_calls", [])]
    embeddings = [event for r in rows for event in r["embedding_requests"]]
    model_usage, embedding_usage = usage_totals(models), usage_totals(embeddings)
    total = (model_usage["cost_usd"] + embedding_usage["cost_usd"]
             if model_usage["cost_usd"] is not None and embedding_usage["cost_usd"] is not None else None)
    def metric(key):
        n = count(key)
        return {"n": n, "N": len(answerable), "rate": n/len(answerable) if answerable else None}
    return {"profile": profile, "split": rows[0]["evaluation"].get("split", "dev"), "cases": len(rows), "answerable_cases": len(answerable),
            "unanswerable_cases": len(rows)-len(answerable),
            "original_query_hit_at_1_literal": metric("raw_hit_at_1_literal"),
            "original_query_evidence_hit_at_3_literal": metric("raw_hit_at_3_literal"),
            "final_model_context_evidence_rate_literal": metric("final_model_context_evidence_literal"),
            "agent_status_counts": {status: sum(r["agent"]["status"] == status for r in rows)
                                    for status in ["answered", "abstain", "error"]},
            "raw_retrieval_errors": sum(bool(r["raw"].get("error")) for r in rows),
            "tool_use": {"n": sum(r["agent"].get("search_count", 0) > 0 for r in successful), "N": len(successful)},
            "search_count_distribution": {str(n): sum(r["agent"].get("search_count", 0) == n for r in rows)
                                          for n in range(3)},
            "answerable_abstentions_unreviewed": sum(r["agent"]["status"] == "abstain" for r in answerable),
            "unanswerable_abstentions_unreviewed": sum(r["agent"]["status"] == "abstain" for r in rows
                                                      if not r["evaluation"]["answerable"]),
            "median_original_query_ms": statistics.median(r["raw"]["elapsed_ms"] for r in rows),
            "median_agent_seconds": statistics.median(r["agent"]["elapsed_seconds"] for r in rows),
            "sum_agent_seconds": sum(r["agent"]["elapsed_seconds"] for r in rows),
            "model_usage": model_usage, "embedding_usage": embedding_usage, "total_cost_usd": total,
            "known_cost_subtotal_usd": model_usage["known_cost_usd"]+embedding_usage["known_cost_usd"],
            "manual_answer_citation_abstention_review": "pending; do not infer semantic correctness from IDs or literal metrics"}
