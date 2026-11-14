# Context DAY07 — task 6

Implementation: [src/context_builder.py](../src/context_builder.py), integrated into [agent runtime](../src/agent_runtime.py) and [CLI](../scripts/run_agent.py). Original starter agentic.py/baseline.py and assignment Markdown remain unchanged.

## Selection and source preservation

- Deduplicate chunk IDs across all retrieval rounds. The same ID with conflicting text/source/page/metadata is an error, not silently accepted.
- Score cumulative relevance by best 1/(60+rank) in any search round. Do not add points for repeated retrieval. Break ties by chunk ID and rebuild the context every round.
- Keep complete original chunk text, including conditions/exceptions within that chunk. Prefix each with [id | source | page N]. Dedup does not merge different sources solely because their text looks alike.
- Count Python len(str) of the entire context, including headers and two-newline separators. Profile budgets remain 4,000 or 6,000 Unicode codepoints, not tokens/bytes.
- Skip chunks that do not fit and continue to later candidates; do not truncate evidence to fit. A whole chunk can still miss surrounding source conditions; human evidence completeness review remains necessary.
- Context builder receives only ranked chunks and budget, never question gold or expected answers.

Every candidate decision stores source/page/metadata, occurrence ranks, best rank score, block/text size, remaining budget and reason selected_complete_chunk / block_exceeds_total_budget / insufficient_remaining_budget. Summary stores unique/duplicate counts, selected/skipped counts, budget use and UTF-8 SHA-256 of the resulting context.

## What each agent run now saves

| File / trace field | Meaning |
|---|---|
| context.txt | Latest constructed context (may not reach model if an error happens first) |
| model_context.txt | Exact evidence context extracted from the last recorded tool message in a model request |
| context_selection.json | Candidate choices/rejections and budget accounting |
| trace.json: events[].context_selection | Selection record at each search round |
| trace.json: model_context_requests | Context text/IDs/hash/size for every recorded model request, with response_received / request_failed / request_recorded |
| trace.json: planned_context_matches_last_model_request | Whether latest planned context equals the evidence text in the last request; null if never sent |
| trace.json: context_transmission | not_sent or the corresponding request/response status |

An empty model_context.txt with not_sent is not a successful empty-evidence request. Request/response metadata distinguishes actual context transport from local packing. Raw tool context in model_calls remains available for independent comparison.

Run the agent as before:

~~~powershell
python -X utf8 scripts/run_agent.py --profile dense_4000 --question "Agile chia dự án thành những đơn vị nào?" --section 1.2
~~~

This agent command calls real APIs. Reading existing saved traces or running the diagnostics below does not.

## Offline tests

~~~powershell
python -B -m unittest tests.test_agent_runtime tests.test_context_builder tests.test_retrieval_methods -v
~~~

24 tests pass: filter/RRF contracts, duplicate identity conflicts, exact source text/conditions, Unicode header+separator budget, oversized candidate skipping, reranking after another round, source-aware citation guards and exact context extraction from serialized model payloads. Fixtures test implementation behavior only, not model quality.

## Dev budget check (no API)

~~~powershell
python -B scripts/check_context_dev.py
~~~

Only 15 answerable dev questions are scored. It takes one fixed TF-IDF ranking per question (top-10, user-provided filters) and repacks it at 800/4,000/6,000 characters. Gold is read exclusively in the evaluator after context construction. No test case is evaluated; no model, embedding or database requests occur. Outputs are under artifacts/context_dev/<UTC timestamp>/.

Observed run: [summary](../artifacts/context_dev/20261114T085712568487Z/summary.json), [traces](../artifacts/context_dev/20261114T085712568487Z/traces.json).

| Budget (characters) | Literal context evidence | Mean used characters | Empty contexts |
|---|---:|---:|---:|
| 800 | 3/15 (20%) | 553.60 | 3/15 |
| 4,000 | 11/15 (73.33%) | 3,072.27 | 1/15 |
| 6,000 | 11/15 (73.33%) | 4,261.27 | 1/15 |

Original-query literal Hit@3 remains 11/15 for all budgets because the ranking is unchanged. These are lexical/context diagnostic numbers, not results for dense/hybrid/agent answers, not reviewed context grades and not a chosen configuration. The larger 6,000 budget adds text on this sample without improving literal coverage. Keep the protocol profiles for the later fair dev experiment.

Do not substitute this check for task 7 (full dev retrieval/context/agent comparisons) or use held-out test results to tune context.
