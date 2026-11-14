"""Budgeted, source-preserving context construction; never accepts questions/gold."""
import copy
import hashlib
from src.retrieval import corpus_fields


def build_context(rankings, budget):
    if type(budget) is not int or budget < 1:
        raise ValueError("budget must be a positive integer")
    candidates, occurrences, best = {}, {}, {}
    total_occurrences = 0
    for round_number, ranking in enumerate(rankings, 1):
        for rank, row in enumerate(ranking, 1):
            required = corpus_fields(row)
            if (not isinstance(row["id"], str) or not row["id"].strip()
                    or not isinstance(row["source"], str) or not row["source"].strip()
                    or not isinstance(row["source_id"], str) or not row["source_id"].strip()
                    or type(row["page"]) is not int or row["page"] < 1
                    or not isinstance(row["text"], str) or not row["text"].strip()
                    or not isinstance(row["metadata"], dict)):
                raise ValueError("Invalid candidate identity/source/page/text")
            cid = row["id"]
            if cid in candidates and corpus_fields(candidates[cid]) != required:
                raise ValueError("ConflictingChunkIdentity")
            candidates[cid] = copy.deepcopy(row)
            occurrences.setdefault(cid, []).append({"search_round": round_number, "rank": rank})
            best[cid] = max(best.get(cid, 0.0), 1.0 / (60 + rank))
            total_occurrences += 1
    ordered = sorted(candidates, key=lambda cid: (-best[cid], cid))
    blocks, ids, decisions = [], [], []
    used = 0
    for cid in ordered:
        row = candidates[cid]
        block = f'[{cid} | {row["source"]} | page {row["page"]}]\n{row["text"]}'
        separator = 2 if blocks else 0
        required = separator + len(block)
        remaining = budget - used
        chosen = required <= remaining
        reason = ("selected_complete_chunk" if chosen else
                  "block_exceeds_total_budget" if len(block) > budget else
                  "insufficient_remaining_budget")
        decisions.append({"id": cid, "source_id": row["source_id"], "source": row["source"],
                          "page": row["page"], "metadata": row["metadata"],
                          "best_reciprocal_rank": best[cid], "occurrences": occurrences[cid],
                          "text_characters": len(row["text"]), "block_characters": len(block),
                          "separator_characters": separator,
                          "remaining_before": remaining, "selected": chosen, "reason": reason})
        if chosen:
            blocks.append(block)
            ids.append(cid)
            used += required
    context = "\n\n".join(blocks)
    assert len(context) == used and used <= budget
    return {"context": context, "context_ids": ids, "context_chars": used,
            "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
            "budget_chars": budget, "remaining_chars": budget-used,
            "unit": "Python len(str), Unicode codepoints including headers and separators",
            "selection_rule": "best reciprocal rank across rounds then chunk ID; dedup ID; no truncation",
            "candidate_occurrences": total_occurrences, "unique_candidates": len(candidates),
            "duplicates_removed": total_occurrences-len(candidates),
            "selected_count": len(ids), "skipped_count": len(candidates)-len(ids),
            "decisions": decisions,
            "semantic_note": "Whole chunks retain original source conditions; completeness/relevance still requires source review."}


def model_context_records(model_calls):
    """Extract actual serialized tool contexts from recorded model requests."""
    records = []
    import json
    for call_index, call in enumerate(model_calls, 1):
        for message in call.get("request", {}).get("messages", []):
            if message.get("role") != "tool":
                continue
            try:
                payload = json.loads(message["content"])
            except (KeyError, TypeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or not isinstance(payload.get("context"), str):
                continue
            context = payload["context"]
            records.append({"model_call_index": call_index, "context": context,
                            "context_ids": payload.get("context_ids", []), "context_chars": len(context),
                            "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
                            "transmission": "response_received" if call.get("response_id")
                                            else "request_failed" if call.get("error") else "request_recorded"})
    return records
