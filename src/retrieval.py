"""Three retrievers on one frozen DAY06 corpus; no benchmark gold is loaded."""
import copy
import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path

from starter.baseline import TfidfIndex, tokenize

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("id", "text", "source_id", "source", "page", "metadata")
FILTER_TYPES = {"section": str, "language": str, "year": int}


def validate_request(query, filters, top_k):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a nonempty string")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if filters is None:
        return {}
    if not isinstance(filters, dict) or set(filters) - FILTER_TYPES.keys():
        raise ValueError("Only section/language/year metadata filters are supported")
    if any(type(value) is not FILTER_TYPES[key] for key, value in filters.items()):
        raise ValueError("Invalid metadata filter value type")
    return dict(filters)


def eligible(chunk, filters):
    return all(key in chunk["metadata"] and type(chunk["metadata"][key]) is type(value)
               and chunk["metadata"][key] == value for key, value in filters.items())


def corpus_fields(chunk):
    return {key: chunk[key] for key in FIELDS}


def validate_chunks(chunks):
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Expected a nonempty chunk array")
    seen = set()
    for chunk in chunks:
        if not isinstance(chunk, dict) or any(key not in chunk for key in FIELDS):
            raise ValueError("Chunk schema mismatch")
        if any(not isinstance(chunk[key], str) or not chunk[key].strip()
               for key in ("id", "text", "source_id", "source")):
            raise ValueError("Invalid chunk text or identity")
        if type(chunk["page"]) is not int or chunk["page"] < 1 or not isinstance(chunk["metadata"], dict):
            raise ValueError("Invalid page or metadata")
        if chunk["id"] in seen:
            raise ValueError("Duplicate chunk ID")
        seen.add(chunk["id"])


def load_snapshot():
    protocol = json.loads((ROOT / "data/benchmark/evaluation_protocol.json").read_text(encoding="utf-8"))
    path = ROOT / protocol["inputs"]["chunks_path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != protocol["inputs"]["chunks_sha256"]:
        raise ValueError("Chunk snapshot differs from evaluation protocol")
    chunks = json.loads(path.read_text(encoding="utf-8"))
    validate_chunks(chunks)
    if len(chunks) != protocol["inputs"]["chunk_count"]:
        raise ValueError("Chunk count differs from evaluation protocol")
    return chunks


class LexicalRetriever:
    """Global DAY06 IDF; filter eligible documents before scoring/ranking."""
    def __init__(self, chunks):
        validate_chunks(chunks)
        self.chunks = copy.deepcopy(chunks)
        self.index = TfidfIndex(self.chunks)
        self.last_search = None

    def search(self, query, *, filters=None, top_k=10):
        filters = validate_request(query, filters, top_k)
        tick = time.perf_counter()
        query_vector = self.index._vector(Counter(tokenize(query)))
        results = []
        allowed = 0
        for chunk, vector in zip(self.chunks, self.index.vectors):
            if not eligible(chunk, filters):
                continue
            allowed += 1
            score = sum(value * vector.get(term, 0.0) for term, value in query_vector.items())
            if score > 0:
                results.append({**corpus_fields(chunk), "score": score,
                                "method": "tfidf", "score_type": "tfidf_cosine"})
        results.sort(key=lambda row: (-row["score"], row["id"]))
        results = [{**row, "rank": i} for i, row in enumerate(results[:top_k], 1)]
        self.last_search = {"method": "tfidf", "filter": filters, "eligible_count": allowed,
                            "returned": len(results), "elapsed_ms": (time.perf_counter()-tick)*1000,
                            "service_cost_usd": 0, "tokenization": "NFC_casefold_word_regex",
                            "idf_scope": "entire_fixed_snapshot"}
        return copy.deepcopy(results)

    def close(self):
        pass


class DensePgvectorRetriever:
    """Reuse real DAY06 adapter; verify DB snapshot before every search/cache read."""
    def __init__(self, chunks):
        validate_chunks(chunks)
        from starter.dense_retriever import DenseRetriever
        self.expected = {c["id"]: corpus_fields(c) for c in copy.deepcopy(chunks)}
        self.backend = DenseRetriever()
        self.cache = {}
        self.last_search = None
        try:
            self.verify_snapshot()
        except Exception:
            self.backend.close()
            raise

    def verify_snapshot(self):
        import psycopg
        with psycopg.connect(self.backend.database_url, connect_timeout=5) as connection:
            rows = connection.execute(
                "SELECT chunk_id,text,document_id,source,page,metadata,vector_dims(embedding) "
                "FROM day6_chunks WHERE strategy=%s", ("B",)).fetchall()
        actual = {row[0]: dict(zip(FIELDS, row[:6])) for row in rows}
        if (len(rows) != len(self.expected) or actual != self.expected
                or any(row[6] != 1536 for row in rows)):
            raise ValueError("pgvector strategy B does not match frozen DAY06 chunks/dimensions")

    def search(self, query, *, filters=None, top_k=10):
        filters = validate_request(query, filters, top_k)
        tick = time.perf_counter()
        self.verify_snapshot()
        key = (query, json.dumps(filters, sort_keys=True), top_k)
        cached = key in self.cache
        if cached:
            results = copy.deepcopy(self.cache[key])
        else:
            results = self.backend.search(query, filters=filters, top_k=top_k)
            ids = [r["id"] for r in results]
            if len(results) > top_k or len(ids) != len(set(ids)):
                raise ValueError("Invalid dense result count/IDs")
            for row in results:
                if (row["id"] not in self.expected
                        or corpus_fields(row) != self.expected[row["id"]]
                        or not eligible(row, filters)
                        or type(row["score"]) not in (float, int)
                        or not math.isfinite(row["score"])):
                    raise ValueError("Dense result inconsistent with snapshot/filter")
            results.sort(key=lambda row: (-row["score"], row["id"]))
            results = [{**row, "rank": i, "method": "dense", "score_type": "cosine_similarity"}
                       for i, row in enumerate(results, 1)]
            self.cache[key] = copy.deepcopy(results)
        self.last_search = {"method": "dense", "filter": filters, "returned": len(results),
                            "elapsed_ms": (time.perf_counter()-tick)*1000, "cache_hit": cached,
                            "service_cost_usd": 0 if cached else None,
                            "cost_note": "Cache is in-process ranked-result cache. Cache miss uses real OpenRouter query embedding; actual charge/token usage not exposed by legacy adapter.",
                            "model": self.backend.model, "dimensions": 1536, "strategy": "B"}
        return copy.deepcopy(results)

    def close(self):
        self.backend.close()


def reciprocal_rank_fusion(rankings, *, k=60, top_k=10):
    """Sum 1/(k+one-based rank) per unique document per branch; never raw scores."""
    if type(k) is not int or k < 1 or type(top_k) is not int or top_k < 1:
        raise ValueError("Positive integer k and top_k required")
    fused = {}
    for branch, ranking in rankings.items():
        seen = set()
        rank = 0
        for row in ranking:
            cid = row["id"]
            if cid in seen:
                continue
            seen.add(cid)
            rank += 1
            if cid not in fused:
                fused[cid] = {**corpus_fields(row), "score": 0.0, "method": "hybrid_rrf",
                              "score_type": "rrf", "components": {}}
            if corpus_fields(row) != corpus_fields(fused[cid]):
                raise ValueError("Same chunk ID has conflicting content across branches")
            contribution = 1.0 / (k + rank)
            fused[cid]["score"] += contribution
            fused[cid]["components"][branch] = {
                "rank": rank, "raw_score": row["score"], "rrf_contribution": contribution}
    rows = sorted(fused.values(), key=lambda row: (-row["score"], row["id"]))[:top_k]
    return [{**row, "rank": rank} for rank, row in enumerate(rows, 1)]


class HybridRetriever:
    def __init__(self, dense, lexical, *, candidate_k=10, rrf_k=60):
        if type(candidate_k) is not int or candidate_k < 1 or type(rrf_k) is not int or rrf_k < 1:
            raise ValueError("Invalid hybrid parameters")
        self.dense, self.lexical = dense, lexical
        self.candidate_k, self.rrf_k = candidate_k, rrf_k
        self.last_search = None

    def search(self, query, *, filters=None, top_k=10):
        filters = validate_request(query, filters, top_k)
        if top_k > self.candidate_k:
            raise ValueError("top_k exceeds configured per-branch candidate_k")
        tick = time.perf_counter()
        dense = self.dense.search(query, filters=filters, top_k=self.candidate_k)
        lexical = self.lexical.search(query, filters=filters, top_k=self.candidate_k)
        if any(not eligible(row, filters) for row in dense + lexical):
            raise ValueError("Hybrid branch failed metadata filter")
        results = reciprocal_rank_fusion({"dense": dense, "lexical": lexical},
                                         k=self.rrf_k, top_k=top_k)
        self.last_search = {"method": "hybrid_rrf", "filter": filters,
                            "candidate_k_per_branch": self.candidate_k, "rrf_k": self.rrf_k,
                            "dense_results": dense, "lexical_results": lexical,
                            "dense_call": copy.deepcopy(self.dense.last_search),
                            "lexical_call": copy.deepcopy(self.lexical.last_search),
                            "returned": len(results), "elapsed_ms": (time.perf_counter()-tick)*1000}
        return results

    def close(self):
        # Hybrid owns neither injected retriever; caller closes shared dense once.
        pass


def build_retriever(method):
    chunks = load_snapshot()
    if method == "lexical":
        return LexicalRetriever(chunks)
    if method == "dense":
        return DensePgvectorRetriever(chunks)
    if method == "hybrid":
        dense = DensePgvectorRetriever(chunks)
        hybrid = HybridRetriever(dense, LexicalRetriever(chunks))
        # A factory-created hybrid owns its components; explicit injected ones do not.
        hybrid.close = dense.close
        return hybrid
    raise ValueError("method must be dense, lexical or hybrid")
