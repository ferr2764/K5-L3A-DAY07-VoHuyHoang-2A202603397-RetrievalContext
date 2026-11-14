"""Build the authored DAY07 benchmark; validate sources without retrieval/API calls."""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DAY6 = ROOT.parent / "K5-L3A-DAY06-VoHuyHoang-2A202603397-DataIngestion"
PDF = DAY6 / "starter/data/Foundations_of_Information_Systems.pdf"
CHUNKS = ROOT / "starter/data/day6/chunks.json"
SOURCE = "foundations-of-information-systems"
OUT = ROOT / "data/benchmark"


def norm(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def exact_quote(text, normalized_quote):
    pattern = r"\s+".join(re.escape(word) for word in normalized_quote.split())
    match = re.search(pattern, unicodedata.normalize("NFC", text))
    return match.group(0) if match else None


NEW_TEST = [
    (62, "direct", "Trong mục 2.2, ba cách chính IT tạo giá trị cho tổ chức là gì?",
     "Tự động hóa hoạt động; tạo thông tin để quản lý con người và nguồn lực; chuyển đổi quy trình hoặc các tác vụ kết hợp (routines).",
     "automation of operation", "combined tasks called routines", True),
    (63, "paraphrase", "FAIS được thiết kế để hỗ trợ điều gì và cải thiện hiệu quả ở cấp nào trong tổ chức?",
     "Hỗ trợ các chức năng kinh doanh cụ thể, tăng hiệu quả và hiệu suất nội bộ của từng phòng ban.",
     "An individual department", "respective department’s functions.", False),
    (65, "metadata_filter", "Trong mục 2.2, business-IT alignment hay strategic alignment được hiểu như thế nào?",
     "Tích hợp chặt chẽ chức năng IT với chiến lược, sứ mệnh và mục tiêu tổ chức; IT trực tiếp hỗ trợ mục tiêu kinh doanh.",
     "Business-IT alignment, or strategic alignment,", "business goals of the organization.", True),
    (66, "conditional", "Nếu business manager chú trọng doanh thu còn IT manager chỉ chú trọng triển khai và bảo trì công nghệ, đây là nguyên nhân lệch pha business–IT nào được sách mô tả?",
     "Different objectives: khác biệt mục tiêu giữa quản lý kinh doanh và quản lý IT.",
     "Different objectives:", "technology implementation and maintenance.", False),
    (67, "conditional", "Khi doanh nghiệp chỉ theo đuổi cost leadership, sách cảnh báo nguy cơ gì đối với nghiên cứu phát triển và đổi mới?",
     "Có thể thiếu nguồn lực cho nghiên cứu và phát triển, từ đó tụt hậu về đổi mới.",
     "For example, if a company focuses only", "terms of innovation.", False),
]

ABSENT = [
    ("d7-dev-16", "dev", "Theo corpus này, VinUni quy định phải lưu log truy cập hệ thống sinh viên trong chính xác bao nhiêu ngày?",
     "Không có chính sách lưu log của VinUni trong corpus; sách nói về quản lý/security nói chung, không quy định số ngày của trường.",
     ["VinUni", "retention", "log"], [34, 38]),
    ("d7-dev-17", "dev", "Theo corpus này, lệ phí thi chứng chỉ SFIA tại Việt Nam năm 2026 là bao nhiêu VND?",
     "Các đoạn SFIA trình bày framework và cấp trách nhiệm, không có bảng lệ phí thi tại Việt Nam năm 2026.",
     ["SFIA", "Vietnam", "VND", "2026", "fee"], [30, 31, 32]),
    ("d7-test-06", "test", "Theo corpus này, giá thuê bao Cohealo + Clinical mỗi tháng năm 2025 là bao nhiêu USD?",
     "Case Cohealo mô tả chức năng, logistics và lợi ích; không công bố giá thuê bao tháng của Clinical năm 2025. Không suy ra giá từ lợi thế chi phí chung.",
     ["Cohealo", "Clinical", "subscription", "monthly", "price"], [70, 71]),
    ("d7-test-07", "test", "Theo corpus này, Walmart đã chi chính xác bao nhiêu USD cho IT trong năm 2025?",
     "Đoạn Walmart minh họa cost leadership, quy mô và hiệu quả vận hành; không có số liệu chi IT năm 2025.",
     ["Walmart", "2025", "spending", "budget"], [67]),
]


def main():
    chunks = load(CHUNKS)
    original = load(DAY6 / "benchmark/questions.json")
    reader = PdfReader(PDF)
    manifest = load(DAY6 / "data/manifest.json")["sources"][0]
    selected = manifest["content_page_counting"]["counted_pdf_pages"]
    pages = {n: norm(reader.pages[n - 1].extract_text() or "") for n in range(30, 73)}
    checks, questions = [], []

    def gold_for(page, quote):
        normalized = norm(quote)
        assert normalized in pages[page], (page, "Evidence missing from PDF")
        golds = []
        chunk_ids = []
        for c in chunks:
            if c["source_id"] == SOURCE and c["page"] == page:
                exact = exact_quote(c["text"], normalized)
                if exact is not None:
                    g = {"source_id": SOURCE, "page": page, "evidence": exact}
                    if g not in golds:
                        golds.append(g)
                    chunk_ids.append(c["id"])
        assert golds, (page, "Gold must fit in one existing chunk")
        # Also accept the same literal evidence on other indexed pages.
        for c in chunks:
            if c["source_id"] != SOURCE or c["page"] == page:
                continue
            exact = exact_quote(c["text"], normalized)
            if exact and normalized in pages[c["page"]]:
                g = {"source_id": SOURCE, "page": c["page"], "evidence": exact}
                if g not in golds:
                    golds.append(g)
                chunk_ids.append(c["id"])
        return golds, chunk_ids

    types = ["direct", "direct", "metadata_filter", "conditional", "conditional",
             "paraphrase", "direct", "paraphrase", "metadata_filter", "paraphrase",
             "conditional", "direct", "conditional", "direct", "paraphrase"]
    for i, old in enumerate([q for q in original if q["split"] == "dev"], 1):
        q = {"id": f"d7-dev-{i:02d}", "split": "dev", "answerable": True,
             "question": old["question"], "expected_answer": old["expected_answer"],
             "expected_behavior": "search_and_answer", "type": types[i-1],
             "filter": old.get("filter"), "origin": f"DAY06 {old['id']} (dev reused)"}
        quote = old["evidence_quote"]
        if old["id"] == "q06":
            q.update(question="Trong Zachman, câu hỏi Where? nhằm tìm hiểu thông tin gì về tổ chức?",
                     expected_answer="Tìm hiểu nơi tổ chức hoạt động.",
                     origin="Adapted DAY06 dev q06: narrow to one fact so gold fits one unchanged chunk.")
            quote = "Where? seeks to learn where the organization operates."
        q["gold"], ids = gold_for(old["gold_page"], quote)
        q["filter_origin"] = "Mục sách nêu sẵn trong câu hỏi." if q["filter"] else None
        questions.append(q)
        checks.append({"id": q["id"], "pdf_evidence_verified": True, "matching_chunk_ids": ids})

    for i, (page, kind, question, answer, start, end, filtered) in enumerate(NEW_TEST, 1):
        text = pages[page]
        a = text.index(start)
        quote = text[a:text.index(end, a) + len(end)]
        gold, ids = gold_for(page, quote)
        q = {"id": f"d7-test-{i:02d}", "split": "test", "answerable": True,
             "question": question, "expected_answer": answer, "expected_behavior": "search_and_answer",
             "type": kind, "filter": {"section": "2.2"} if filtered else None,
             "filter_origin": "Mục 2.2 được nêu sẵn trong câu hỏi." if filtered else None,
             "origin": "New DAY07 held-out question; not a DAY06 test/reserve question.",
             "gold": gold}
        questions.append(q)
        checks.append({"id": q["id"], "pdf_evidence_verified": True, "matching_chunk_ids": ids})

    absence_checks = []
    for qid, split, question, reason, terms, relevant in ABSENT:
        search = []
        for term in terms:
            found = sorted({c["page"] for c in chunks if term.casefold() in norm(c["text"]).casefold()})
            search.append({"term": term, "matching_indexed_pages": found})
        questions.append({"id": qid, "split": split, "answerable": False,
                          "question": question, "expected_answer": "Không đủ bằng chứng trong bộ tài liệu để trả lời con số được hỏi.",
                          "expected_behavior": "search_and_abstain", "type": "insufficient_evidence",
                          "gold": [], "filter": None, "absence_reason": reason,
                          "absence_verification": {"scope": "All 162 indexed DAY06 B chunks across 34 content pages; not a claim about unindexed PDF pages or external knowledge.",
                                                   "indexed_pages_checked": selected,
                                                   "relevant_pages_read": relevant, "term_scan": search,
                                                   "method": "Inspect topic passages and requested entity/date/unit; scan full indexed text. Keyword absence alone or a retrieval miss is not proof."}})
        absence_checks.append({"id": qid, "reason": reason, "relevant_pages_read": relevant, "term_scan": search})

    questions.sort(key=lambda q: (q["split"], q["id"]))
    counts = Counter((q["split"], q["answerable"]) for q in questions)
    assert counts == {("dev", True): 15, ("dev", False): 2, ("test", True): 5, ("test", False): 2}
    assert len({q["id"] for q in questions}) == 24
    old_test_answers = {norm(q["expected_answer"]).casefold() for q in original if q["split"] == "test"}
    assert not any(norm(q["expected_answer"]).casefold() in old_test_answers for q in questions if q["split"] == "test" and q["answerable"])
    OUT.mkdir(parents=True, exist_ok=True)
    dump(OUT / "questions.json", questions)
    dump(OUT / "answerable_questions.json", [q for q in questions if q["answerable"]])
    # Gold-free case metadata for agent metric aggregation. Do not send answerable to the controller.
    dump(OUT / "cases.json", [{k: q[k] for k in ("id", "split", "question", "answerable", "expected_behavior")} for q in questions])
    dump(OUT / "validation.json", {
        "source_id": SOURCE, "pdf_path_from_day07": str(PDF.relative_to(ROOT.parent)),
        "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
        "chunks_path": CHUNKS.relative_to(ROOT).as_posix(),
        "chunks_sha256": hashlib.sha256(CHUNKS.read_bytes()).hexdigest(),
        "day6_questions_sha256": hashlib.sha256((DAY6 / "benchmark/questions.json").read_bytes()).hexdigest(),
        "questions_sha256": hashlib.sha256((OUT / "questions.json").read_bytes()).hexdigest(),
        "chunk_count": len(chunks), "indexed_content_page_count": len(selected),
        "counts": {"dev_answerable": 15, "dev_unanswerable": 2, "test_answerable": 5, "test_unanswerable": 2},
        "evidence_checks": checks, "absence_checks": absence_checks,
        "status": "authored_and_source_checked_before_DAY07_retrieval_experiments; no benchmark run",
        "reviewer": "Codex assisted authoring/source review; student review recommended",
        "test_independence_limit": "New question/answer targets versus DAY06 test, but same book and existing index. Test gold was inspected for benchmark construction; do not inspect it to tune retrieval."
    })
    print("Created 24 DAY07 cases: 17 dev / 7 test; all 20 answerable golds verified on PDF and within existing chunks. No API/retrieval experiments.")


if __name__ == "__main__":
    main()
