"""Summarize two predeclared improvement experiments and inspect saved DEV errors.
No model/API calls, no test data, no rewriting original metrics or answers.
"""
import copy
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "artifacts/dev_retries/20261114T093849461754Z"
ORIGINAL = ROOT / "artifacts/dev_benchmark/20261114T092856910861Z"
OUT = ROOT / "artifacts/dev_improvements"
PDF = ROOT.parent / "K5-L3A-DAY06-VoHuyHoang-2A202603397-DataIngestion/starter/data/Foundations_of_Information_Systems.pdf"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(text):
    return " ".join(text.split())


def main():
    OUT.mkdir(exist_ok=True)
    records = read(RUN / "effective_records.json")
    summary = read(RUN / "summary.json")
    profiles = {p["profile"]: p for p in summary["profiles"]}
    lookup = {(r["profile"], r["query_id"]): r for r in records}
    protocol = read(ROOT / "data/benchmark/evaluation_protocol.json")
    config = {p["id"]: p for p in protocol["profiles"]}
    original_manifest = read(ORIGINAL / "run_manifest.json")
    retry_manifest = read(RUN / "run_manifest.json")
    assert retry_manifest["original_manifest"]["controller"] == original_manifest["controller"]
    assert hashlib.sha256((ROOT / "data/benchmark/questions.json").read_bytes()).hexdigest() == protocol["inputs"]["questions_sha256"]
    cases = {q["id"]: q for q in read(ROOT / "data/benchmark/questions.json") if q["split"] == "dev"}
    chunks = {c["id"]: c for c in read(ROOT / protocol["inputs"]["chunks_path"])}
    pdf = PdfReader(PDF)
    review_provenance = {
        "reviewer": "Codex (AI assistant)",
        "method": "Read saved dev answers, citations, original/rewritten rankings, context decisions and PDF evidence; do not infer semantic grades from IDs.",
        "human_confirmation": "pending",
        "scope": "Selected error cases only, not full dev answer grading or model selection."
    }

    def snapshot(profile):
        p = profiles[profile]
        return {key: p[key] for key in [
            "original_query_hit_at_1_literal", "original_query_evidence_hit_at_3_literal",
            "final_model_context_evidence_rate_literal", "median_original_query_ms",
            "median_agent_seconds", "total_cost_usd", "agent_status_counts"]}

    experiments = [
        {"id": "improvement_1_rrf", "before": "dense_4000", "after": "hybrid_4000",
         "hypothesis_predeclared": "Combine exact lexical terms and semantic retrieval with RRF to improve evidence ranking/coverage.",
         "change": "Dense alone -> dense + TF-IDF, each branch top-10, RRF k=60; same 4000-char context and model/prompt.",
         "before_metrics": snapshot("dense_4000"), "after_metrics": snapshot("hybrid_4000"),
         "observed_result": "Did not improve aggregate literal retrieval/context: Hit@1 8/15 -> 8/15; Hit@3 13/15 -> 12/15; context 13/15 -> 12/15. Report regression honestly; do not tune using test."},
        {"id": "improvement_2_context", "before": "hybrid_4000", "after": "hybrid_6000",
         "hypothesis_predeclared": "Larger context budget can retain lower-ranked relevant whole chunks skipped at 4000 chars.",
         "change": "Only context budget 4000 -> 6000; same hybrid candidates/RRF/filter/model/prompt/limits.",
         "before_metrics": snapshot("hybrid_4000"), "after_metrics": snapshot("hybrid_6000"),
         "observed_result": "Hit@1/Hit@3 unchanged 8/15 and 12/15; context 12/15 -> 14/15. More model input and cost; not proof of better overall grounded answers."}
    ]
    for key in ["method", "return_top_k", "max_searches", "max_model_decisions", "rrf_k"]:
        assert config["hybrid_4000"][key] == config["hybrid_6000"][key]

    def observation(profile, qid, grade, citation_support, reason):
        r = lookup[profile, qid]
        case = cases[qid]
        events = [e for e in r["agent"]["events"] if e["event"] == "search"]
        targets = []
        for e in events:
            for rank, hit in enumerate(e["results"], 1):
                if any(hit["source_id"] == g["source_id"] and hit["page"] == g["page"]
                       and norm(g["evidence"]) in norm(hit["text"]) for g in case["gold"]):
                    decision = next(d for d in e["context_selection"]["decisions"] if d["id"] == hit["id"])
                    targets.append({"chunk_id": hit["id"], "page": hit["page"], "rank": rank,
                                    "decision": decision})
        for gold in case["gold"]:
            assert norm(gold["evidence"]) in norm(pdf.pages[gold["page"]-1].extract_text())
        cited = [{"id": cid, "page": chunks[cid]["page"], "text": chunks[cid]["text"],
                  "in_context": cid in r["agent"]["context_ids"]}
                 for cid in r["agent"]["citations"]]
        assert len(cited) == len(citation_support)
        base = RUN if "original_attempt_status" in r else ORIGINAL
        return {"profile": profile, "query_id": qid, "question": case["question"],
                "expected_answer": case["expected_answer"], "gold": case["gold"],
                "trace_path": (base/profile/qid/"agent_trace.json").relative_to(ROOT).as_posix(),
                "status": r["agent"]["status"], "answer": r["agent"]["answer"],
                "queries": [e["query"] for e in events],
                "target_candidates": targets, "citations": cited,
                "context_evidence_literal": r["evaluation"]["final_model_context_evidence_literal"],
                "grounded_answer_0_2": grade, "citation_support": citation_support,
                "reason": reason, "provenance": review_provenance}

    errors = [
        {"id": "sfia_level5_budget", "query_id": "d7-dev-05", "source_page": 32,
         "cause": "Gold chunk at agent hybrid rank 6 is 1046 chars including header; 4000-budget remaining 160 chars so it is skipped. Model confuses Level 6 with expected Level 5.",
         "hypothesis": "Keep same ranking and increase budget to fit the whole SFIA level-definition chunk.",
         "before": observation("hybrid_4000", "d7-dev-05", 0, [False],
                 "Answer says Level 6; PDF explicitly assigns broad direction and self-initiation to Level 5. Cited chunk describes levels 6/7 and does not support this answer."),
         "after": observation("hybrid_6000", "d7-dev-05", 2, [True],
                 "Same query/candidate ranking; 6000-budget remaining 1410 chars permits the 1046-char target. Answer correctly identifies Level 5 with supported citation."),
         "result": "Context evidence false -> true; selected-case answer grade 0 -> 2; no claim about all dev answers."},
        {"id": "velocity_budget_unsupported_citation", "query_id": "d7-dev-11", "source_page": 56,
         "cause": "Gold Velocity chunk at hybrid rank 6 is 932 chars; 4000-budget remaining 191 chars skips it. Answer names Velocity but cites a chunk defining Volume/Variety, not the requested relationship.",
         "hypothesis": "Increase context budget while holding the hybrid ranking fixed to retain the explicit Velocity definition.",
         "before": observation("hybrid_4000", "d7-dev-11", 0, [False],
                 "Velocity label happens to be correct but the cited eab422... chunk has Volume/Variety and does not support the real-time Velocity claim; rubric 0 for missing evidence."),
         "after": observation("hybrid_6000", "d7-dev-11", 2, [True],
                 "932-char Velocity block fits with 1231 chars remaining, answer cites the explicit definition and relevant flash-sale example."),
         "result": "Context evidence false -> true; selected-case grounded grade 0 -> 2; original Vietnamese-query Hit@3 remains a miss."},
        {"id": "sfia_level3_rrf_regression", "query_id": "d7-dev-04", "source_page": 32,
         "cause": "Original dense ranks correct Level-3 chunk 3rd; RRF moves it to 4th. Agent rewritten query moves target to dense rank 7/hybrid rank 8; context budgets both skip it.",
         "hypothesis": "RRF might preserve useful exact SFIA terms; larger context might recover lower-ranked evidence.",
         "before": observation("dense_4000", "d7-dev-04", 0, [],
                 "False abstention on an answerable question; original query had a valid top-3 hit but agent query/context omitted it."),
         "after": observation("hybrid_6000", "d7-dev-04", 0, [False],
                 "Still omits Level-3 chunk, answers Level 5 and cites a Level-1 introductory chunk. 6000 budget remaining 439 chars is still less than target 1046."),
         "result": "Not fixed; raw Hit@3 true -> false and answer remains grade 0. Do not equate answered with improvement."}
    ]
    for qid in ["d7-dev-05", "d7-dev-11"]:
        left = lookup["hybrid_4000", qid]["agent"]
        right = lookup["hybrid_6000", qid]["agent"]
        le = [e for e in left["events"] if e["event"] == "search"]
        re = [e for e in right["events"] if e["event"] == "search"]
        assert [e["query"] for e in le] == [e["query"] for e in re]
        assert [[h["id"] for h in e["results"]] for e in le] == [[h["id"] for h in e["results"]] for e in re]
    analysis = {"scope": "Two predeclared improvements already executed in task 7, plus three source-reviewed DEV error cases. No new experiments/API calls or test evaluation.",
                "run": RUN.relative_to(ROOT).as_posix(), "experiments": experiments,
                "errors": errors, "provenance": review_provenance,
                "selected_configuration": None,
                "input_hashes": {
                    "effective_records_sha256": hashlib.sha256((RUN / "effective_records.json").read_bytes()).hexdigest(),
                    "protocol_sha256": hashlib.sha256((ROOT / "data/benchmark/evaluation_protocol.json").read_bytes()).hexdigest(),
                    "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest()},
                "limitations": ["Only selected dev cases semantically reviewed; no full answer/citation score yet.",
                                "Original 49 successes plus 19 restored-credit retries; preserve all attempts and billing.",
                                "Single observation/profile; model/provider nondeterminism and concurrent latency.",
                                "Larger context does not fix low-ranking evidence or all citation-format errors."]}
    (OUT/"analysis.json").write_text(json.dumps(analysis,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    md = ["# Hai thí nghiệm cải thiện và phân tích lỗi dev\n\n",
          "Các cấu hình đã chốt trước dev và đã chạy thật ở bước 7; bước 8 này phân tích kết quả đã lưu, không gọi API lại hoặc thay câu trả lời. Nhãn nội dung do Codex hỗ trợ đối chiếu PDF, **chưa được học viên xác nhận**. Không chạy test, chưa chọn cấu hình thắng.\n\n",
          "| Thí nghiệm | Trước → sau | Giả thuyết | Hit@1 | Hit@3 | Context Evidence Rate |\n",
          "|---|---|---|---|---|---|\n",
          "| Cải thiện 1 | dense_4000 → hybrid_4000 | RRF kết hợp lexical và semantic | 8/15 → 8/15 | 13/15 → 12/15 | 13/15 → 12/15 |\n",
          "| Cải thiện 2 | hybrid_4000 → hybrid_6000 | Tăng budget để giữ chunk xếp thấp | 8/15 → 8/15 | 12/15 → 12/15 | 12/15 → 14/15 |\n\n",
          "RRF là một phương pháp mới và đồng thời một cấu hình thử cải thiện; kết quả aggregate bị giảm vẫn là thí nghiệm hợp lệ. Cải thiện 2 chỉ thay budget; hai lỗi minh họa dưới đây có cùng query agent và cùng toàn bộ thứ tự candidate, giúp đối chiếu trực tiếp tác động của đóng gói context.\n\n"]
    for error in errors:
        md += ["## "+error["query_id"]+" — "+error["id"]+"\n\n",
               "- Trang PDF: "+str(error["source_page"])+". Đáp án: "+error["before"]["expected_answer"]+"\n",
               "- Nguyên nhân: "+error["cause"]+"\n",
               "- Giả thuyết: "+error["hypothesis"]+"\n",
               "- Trước ("+error["before"]["profile"]+"): "+error["before"]["answer"]+"\n",
               "- Sau ("+error["after"]["profile"]+"): "+error["after"]["answer"]+"\n",
               "- Kết quả: "+error["result"]+"\n",
               "- Trace: [trước](../"+error["before"]["trace_path"]+"), [sau](../"+error["after"]["trace_path"]+").\n\n"]
    md += ["## Chi phí, đánh đổi và giới hạn\n\n"]
    for profile in ["dense_4000","hybrid_4000","hybrid_6000"]:
        p=profiles[profile]
        md += ["- "+profile+": cost của case hiệu lực $"+format(p["total_cost_usd"],".8f")+
               "; median agent "+format(p["median_agent_seconds"],".3f")+" giây.\n"]
    md += ["\nTổng cost benchmark đã biết gồm cả attempt gốc và retry là $0.08380398; không cộng thêm các cost case hiệu lực vào tổng này. Chi phí request lỗi không có usage vẫn chưa đối soát. Latency là phép đo chạy đồng thời và ở hai thời điểm, không coi là thử nghiệm cô lập.\n\n",
           "Hai lỗi được sửa theo evidence/đáp án không chứng minh mọi câu đều tốt hơn. d7-dev-04 vẫn sai; một số case MDM bị từ chối do định dạng citation nhóm. Chưa sửa guard hay rerun các case đó trong bước này để tránh trộn pipeline khác vào kết quả đã đo. Nếu sửa tiếp, tạo config/run mới trên dev và ghi thay đổi, giữ nguyên test.\n\n",
           "Dữ liệu máy đọc: [analysis.json](../artifacts/dev_improvements/analysis.json). Tái tạo phân tích không gọi API: python scripts/analyze_dev_improvements.py. Các giá trị answer grade trong file chỉ thuộc các case đã đọc, không tự điền cho toàn bộ dev. Cần chấm đủ grounded answers, citation và abstention trước khi chọn cấu hình theo protocol.\n"]
    md += ["\n## Dependency để tái đối chiếu PDF\n\n",
           "Script phân tích cần pypdf; môi trường DAY07 ban đầu chỉ có SDK/API dependencies. Nếu thiếu, cài thêm dependency phân tích riêng (không thay requirements gốc):\n\n",
           "~~~powershell\npython -m pip install -r scripts/requirements-analysis.txt\npython scripts/analyze_dev_improvements.py\n~~~\n"]
    (ROOT/"docs/DEV_IMPROVEMENTS.md").write_text("".join(md),encoding="utf-8")
    print("Recorded two measured improvements and three source-checked dev error dossiers; no new API calls/test data.")


if __name__ == "__main__":
    main()
