"""Record source-reviewed DEV labels and freeze selection before test API calls."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "artifacts/dev_retries/20261114T093849461754Z"
BASE = ROOT / "artifacts/dev_benchmark/20261114T092856910861Z"
BAD = {"dense_4000": {4,5,8,14,15}, "lexical_4000": {4,5,10,11,15},
       "hybrid_4000": {4,5,11,14}, "hybrid_6000": {4,9,14}}
REASONS = {
1: "Nêu sprint và các bước, xem xét/điều chỉnh sau sprint; đoạn Agile trên trang PDF 30 hỗ trợ.",
2: "Liệt kê đủ EDM/APO/BAI/DSS/MEA với tên đầy đủ; text/caption COBIT trang 30 hỗ trợ.",
3: "Liệt kê đủ bảy yếu tố McKinsey 7-S; trang 31 hỗ trợ.",
4: "Gold là Level 3 Apply; đoạn SFIA trang 32 nêu rõ general supervision, autonomy/nonroutine/oversee.",
5: "Gold là Level 5 Ensure and Advise; trang 32 nêu broad direction và self-initiate.",
6: "Where? tìm nơi tổ chức hoạt động; mục Zachman trang 33 hỗ trợ.",
7: "Nêu cơ sở giáo dục đại học và chuẩn bị nghề IS bậc đại học; IS2020 trang 34 hỗ trợ.",
8: "Đủ kỹ năng, kinh nghiệm, đặc điểm cá nhân và làm việc hiệu quả; định nghĩa trang 36, ví dụ trang 36–38 hỗ trợ phần mở rộng.",
9: "Phân biệt DAMA-DMBOK kỹ thuật và MIKE2.0 kinh doanh; trang 55 hỗ trợ trọng tâm chính.",
10: "Veracity: độ tin cậy/chính xác và chất lượng/nhất quán; trang 56 hỗ trợ.",
11: "Velocity cần evidence tốc độ phát sinh/thu thập và xử lý thời gian thực; trang 56 là định nghĩa chuẩn.",
12: "Đủ integrity, availability, performance và mục tiêu vận hành; trang 56 hỗ trợ.",
13: "Tên Date of Birth/Birth Date khác nhưng định nghĩa thống nhất để phân tích/báo cáo đúng; trang 57 hỗ trợ.",
14: "MDM là nguồn sự thật duy nhất chính xác và loại bất nhất/trao đổi dữ liệu; trang 57 hỗ trợ.",
15: "Phân biệt strategic planning và management control; trang 58–59 hỗ trợ mục tiêu, cấp quản lý và hoạt động.",
16: "Câu thiếu chính sách log riêng của VinUni trong corpus; đáp án xuất bản chỉ nói không đủ evidence, không thêm số ngày.",
17: "Corpus không có lệ phí SFIA tại Việt Nam năm 2026; đáp án xuất bản từ chối, không đoán giá."}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = read(DEV / "effective_records.json")
    protocol = read(ROOT / "data/benchmark/evaluation_protocol.json")
    cases = {q["id"]: q for q in read(ROOT / "data/benchmark/questions.json") if q["split"] == "dev"}
    chunks = {c["id"]: c for c in read(ROOT / protocol["inputs"]["chunks_path"])}
    reviews = []
    for row in rows:
        profile, qid, agent = row["profile"], row["query_id"], row["agent"]
        n = int(qid.rsplit("-",1)[1])
        case = cases[qid]
        assert agent["status"] != "error"
        grade = (0 if n in BAD[profile] else 2) if case["answerable"] else None
        reason = REASONS[n]
        if case["answerable"] and agent["status"] == "abstain":
            assert grade == 0
            reason += " Agent từ chối câu có đáp án, chấm 0; " + agent["stop_reason"] + "."
        elif case["answerable"] and grade == 0:
            if n in (4,5):
                reason += " Agent chọn nhầm cấp SFIA và citation không hỗ trợ điều kiện hỏi."
            elif n == 11:
                reason += "Nêu đúng nhãn Velocity nhưng citation eab422... chỉ có Volume/Variety, thiếu evidence cho claim chính."
        support, citation_reviews = [], []
        for cid in agent["citations"]:
            c = chunks[cid]
            valid = (cid in agent["model_context_ids"] and
                     c["text"] in agent["model_context"])
            # Explicit source-read adjudications, not inference from literal hit.
            if n in (4,5) and grade == 0:
                valid = False
            if n == 11 and cid.startswith("eab422"):
                valid = False
            if n == 8 and cid.startswith("5b892"):
                valid = False
            support.append(valid)
            citation_reviews.append({"id":cid,"source_id":c["source_id"],"page":c["page"],
                "quote":c["text"],"supports_answer":valid,
                "reason":"Đoạn hỗ trợ ít nhất một khẳng định được dẫn trong đáp án và có trong context cuối." if valid else
                         "ID có thể hợp lệ nhưng đoạn không hỗ trợ khẳng định được gắn citation (sai cấp SFIA, thiếu Velocity hoặc đoạn giới thiệu DOL quá chung)."})
        reviews.append({"profile":profile,"query_id":qid,"split":"dev","answerable":case["answerable"],
            "answer_grade":grade,"citation_support":support,"citation_reviews":citation_reviews,
            "abstention_correct":(agent["status"]=="abstain") if not case["answerable"] else None,
            "reason":reason,"answer":agent["answer"],"expected_answer":case["expected_answer"],
            "provenance":{"reviewer":"Codex (AI assistant)","human_confirmation":"pending",
              "method":"Content review of saved answers, citations/context and source passages after dev; not blind, not a human review."}})
    scored = []
    metrics = {p["profile"]:p for p in read(DEV/"summary.json")["profiles"]}
    for profile in BAD:
        rs = [r for r in reviews if r["profile"]==profile]
        answerable = [r for r in rs if r["answerable"]]
        unsupported = [r for r in rs if not r["answerable"]]
        nvalid = sum(sum(r["citation_support"]) for r in rs)
        ncite = sum(len(r["citation_support"]) for r in rs)
        grade = sum(r["answer_grade"] for r in answerable)/len(answerable)
        m = metrics[profile]
        abstain = sum(r["abstention_correct"] for r in unsupported)/len(unsupported)
        citation = nvalid/ncite if ncite else -1
        # Negative values turn minimization of cost/latency/budget into sort order.
        cost = m["total_cost_usd"]
        budget = next(p["context_budget_chars"] for p in protocol["profiles"] if p["id"]==profile)
        key = [0,grade,abstain,citation,m["final_model_context_evidence_rate_literal"]["rate"],
               m["original_query_evidence_hit_at_3_literal"]["rate"],m["original_query_hit_at_1_literal"]["rate"],
               -cost,-m["median_agent_seconds"],-budget]
        scored.append({"profile":profile,"system_errors":0,"grounded_answer_counts":{
                str(g):sum(r["answer_grade"]==g for r in answerable) for g in [0,1,2]},
                "grounded_answer_mean":grade,"abstention":{"n":sum(r["abstention_correct"] for r in unsupported),"N":len(unsupported)},
                "citation_validity":{"n":nvalid,"N":ncite},"selection_key":key,
                "cost_usd_effective_cases":cost})
    # Stable alphabetical fallback after all protocol criteria are tied.
    scored.sort(key=lambda r:r["profile"])
    scored.sort(key=lambda r:tuple(r["selection_key"]),reverse=True)
    winner = scored[0]["profile"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "artifacts/selection" / stamp
    out.mkdir(parents=True,exist_ok=False)
    write = lambda n,d:(out/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write("dev_reviews.json",reviews)
    write("dev_selection.json",{"scoring":scored,"winner":winner,"selection_order":protocol["selection_order"],
          "note":"AI-assisted semantic review recorded before test; student confirmation pending. No test outcomes used."})
    original = read(BASE/"run_manifest.json")
    paths=["src/agent_runtime.py","src/context_builder.py","src/retrieval.py","src/dev_evaluation.py",
           "starter/dense_retriever.py","src/prompts/agent_system.txt","data/benchmark/evaluation_protocol.json",
           protocol["inputs"]["chunks_path"],protocol["inputs"]["questions_path"]]
    selected = next(p for p in protocol["profiles"] if p["id"]==winner)
    baseline = next(p for p in protocol["profiles"] if p["id"]=="dense_4000")
    freeze={"created_at_utc":stamp,"scope":"Freeze BEFORE test API calls",
        "baseline":baseline,"selected":selected,"controller":original["controller"],
        "selection_rule":protocol["selection_order"],"dev_run":DEV.relative_to(ROOT).as_posix(),
        "dev_reviews_sha256":digest(out/"dev_reviews.json"),"dev_selection_sha256":digest(out/"dev_selection.json"),
        "file_hashes":{p:digest(ROOT/p) for p in paths},
        "review_provenance":"Codex source/content review; student confirmation pending",
        "no_test_tuning":True}
    write("freeze.json",freeze)
    print(json.dumps(scored,ensure_ascii=False,indent=2))
    print("FREEZE:",(out/"freeze.json").relative_to(ROOT).as_posix())


if __name__=="__main__":
    main()
