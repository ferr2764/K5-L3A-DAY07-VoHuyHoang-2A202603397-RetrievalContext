# Retrieval DAY07 — task 4

Implementation: [src/retrieval.py](../src/retrieval.py). Existing assignment files and starter baseline remain unchanged.

| Method | Implementation | Score |
|---|---|---|
| Dense | Real DAY06 pgvector B through starter/dense_retriever.py | 1 - cosine distance |
| Lexical | Existing TF-IDF tokenizer/vectorizer, global fixed-corpus IDF, filter eligible docs before scoring and cutoff | TF-IDF cosine |
| Hybrid | Dense top-10 + lexical top-10; reciprocal rank fusion k=60, top-10 output | sum 1/(60 + rank) |

RRF uses ranks, never adds incomparable raw cosine/TF-IDF scores. Missing documents contribute zero; duplicate IDs count once per branch. Ties break by chunk ID. Each result has id, text, source_id, source, page, metadata, score, rank, method and score_type. Hybrid components include each branch rank, raw score and RRF contribution; last_search retains both branch rankings and timing.

Protocol: [evaluation_protocol.json](../data/benchmark/evaluation_protocol.json). The retrievers load only its chunk input metadata and the frozen chunks, not benchmark gold/answers. load_snapshot checks SHA-256 and unique IDs. Dense checks DB B IDs/text/source/page/metadata/dimensions against the local snapshot before every search; mismatch fails instead of silently comparing different corpora.

All methods accept search(query, filters=None, top_k=10). Supported filters: section/language string, year integer (not boolean). Unknown filters fail. No-match filters remain empty; no automatic broadening. Lexical uses NFC + casefold + word-regex; English source/Vietnamese query mismatch is a limitation to measure on dev, not a reason to change test labels.

Dense uses a per-instance in-memory cache of ranked results keyed by query/filter/top-k. Repeated identical calls, including hybrid after dense, reuse the result but verify DB snapshot again. last_search.cache_hit discloses reuse. Cache miss calls the real OpenRouter API; token/USD usage is unknown with the existing adapter and recorded as null. Share the same dense instance for a fair cache-reuse experiment. Service cost 0 on a cache hit means no new embedding request, not zero original construction cost. Snapshot checking is included in recorded elapsed_ms.

## Offline verification

From DAY07 root:

~~~powershell
python -B -m unittest discover -s tests -p test_retrieval_methods.py -v
~~~

Only this new test file is selected: the user's existing tests/test_dense.py executes a real API request at import. The eight tests use fixtures for algorithms/contracts, never fake quality results. They also verify frozen real chunk loading without reading held-out questions.

## One explicit retrieval call

Dependencies: use the DAY07 virtual environment with starter/requirements.txt installed. Dense/hybrid require DAY06 database running and starter/.env configured. Full environment setup remains in the existing project guidance.

~~~powershell
python scripts/search_retrieval.py --method lexical --query "Agile chia dự án thành những đơn vị nào?" --section 1.2 --top-k 10
python scripts/search_retrieval.py --method dense --query "Agile chia dự án thành những đơn vị nào?" --section 1.2 --top-k 10
python scripts/search_retrieval.py --method hybrid --query "Agile chia dự án thành những đơn vị nào?" --section 1.2 --top-k 10
~~~

Optional --output artifacts/my_search.json writes a fresh JSON; existing file paths are rejected. Each output includes the full ranking, top3 and last_search. Dense/hybrid are paid API calls when their process-local cache is empty. CLI processes do not share a cache.

Explicit integration check (one dense query then shared-cache hybrid; no benchmark metrics):

~~~powershell
python scripts/check_retrieval_methods.py
~~~

This writes artifacts/retrieval_smoke.json and may overwrite that smoke artifact. It uses the previously shown Agile query and a section filter, not benchmark test cases. No mock fallback. Connection errors propagate; do not report unavailable backend as an empty valid result.

## What task 4 does not do

No agent controller, context budget packing, benchmark scoring, dev configuration selection or test evaluation is implemented here. hybrid_4000 and hybrid_6000 will use the same retriever; only their later context construction differs. The protocol JSON remains the pre-experiment declaration, not a claim the whole pipeline is implemented.

RRF reference: [Cormack, Clarke and Buettcher, SIGIR 2009](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf). pgvector reference: [official documentation](https://github.com/pgvector/pgvector).
