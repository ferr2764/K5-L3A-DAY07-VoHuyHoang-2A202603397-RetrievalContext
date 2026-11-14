"""Source-based test content adjudication; no model calls or pipeline modifications.
Labels below record Codex reading of the saved answers and original PDF, not
automatic inference from citation IDs, exact strings, or retrieval success.
"""
import hashlib
import json
import sys
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from starter.agent_metrics import aggregate
RUN=ROOT/"artifacts/test_benchmark/20261114T095337524594Z"
FREEZE=ROOT/"artifacts/selection/20261114T095320637430Z/freeze.json"
OUT=ROOT/"artifacts/test_review/20261114T095337524594Z"
PDF=ROOT.parent/"K5-L3A-DAY06-VoHuyHoang-2A202603397-DataIngestion/starter/data/Foundations_of_Information_Systems.pdf"

def read(p):return json.loads(p.read_text(encoding="utf-8"))
def norm(t):return " ".join(t.split())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

# Explicit content labels following the predeclared 0/1/2 grounded rubric.
GRADES={"dense_4000":{1:2,2:2,3:2,4:1,5:1},
        "hybrid_6000":{1:2,2:2,3:0,4:1,5:1}}
REASONS={
1:"Đáp án nêu đủ automation, information generation và transformation/routines; text trang PDF 62 và citation hỗ trợ đủ ba ý.",
2:"Đáp án đúng hỗ trợ chức năng kinh doanh cụ thể và tăng hiệu quả từng phòng ban; các ví dụ accounting/finance/operations/marketing/HR có ở trang 63.",
3:"Dense nêu đúng tích hợp IT với strategy/mission/objectives và vai trò đối tác chiến lược, giao tiếp; hai đoạn trang 65 và 66 hỗ trợ. Hybrid xuất bản lời từ chối vì citation nhóm [id1, id2] bị guard loại; chấm câu trả lời xuất bản 0 dù bản rejected có ý đúng.",
4:"Đúng ý chính Different objectives. Tuy nhiên đáp án thêm quan hệ nhân quả 'sự khác biệt này dẫn đến thiếu hiểu biết về chuyên môn'. Trang 66 liệt kê Different objectives và Lack of expertise awareness như các nguyên nhân riêng, không thiết lập quan hệ nhân quả đó; chấm đúng một phần 1/2.",
5:"Đúng nguy cơ thiếu R&D và chậm đổi mới. Nhưng đáp án thêm suy luận mất lợi thế cạnh tranh dài hạn và ví dụ không đầu tư tùy chỉnh/hỗ trợ sẽ tụt hậu. Đoạn trích trang 67 chỉ mở tình huống chuyển sang customer orientation; phần nối trang 68 nói chi phí ban đầu/benefits, không chứng minh đầy đủ ví dụ kết luận của model; chấm 1/2.",
6:"Corpus index chỉ có mô tả chức năng/case Cohealo (trang 70–71), không có giá thuê bao tháng Clinical năm 2025. Đáp án xuất bản thực sự từ chối, không thêm giá hay khẳng định suy đoán.",
7:"Đoạn Walmart trang 67 minh họa cost leadership, không có ngân sách IT năm 2025. Đáp án xuất bản từ chối, không nêu con số ngoài nguồn."}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    frozen=read(FREEZE)
    for name,value in frozen["file_hashes"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value,name
    cases=[q for q in read(ROOT/"data/benchmark/questions.json") if q["split"]=="test"]
    byid={q["id"]:q for q in cases}
    chunks={c["id"]:c for c in read(ROOT/"starter/data/day6/chunks.json")}
    reader=PdfReader(PDF)
    pdf_pages={n:norm(reader.pages[n-1].extract_text() or "") for n in range(30,73)}
    provenance={"reviewer":"Codex (AI assistant)","human_confirmation":"pending",
        "method":"Read all 14 published answers, final model contexts, every published citation and corresponding PDF passages; inspect rejected answer separately, do not score it as published.",
        "bias_risk":"Assistant also authored benchmark/code and saw metrics; not an independent or blinded human review.",
        "citation_policy":"Binary full-support score for the attached claim bundle; partial support recorded explicitly, not counted as fully valid. Correct ID/source alone is insufficient."}
    all_reviews=[]
    summaries=[]
    for profile in ["dense_4000","hybrid_6000"]:
        rows=read(RUN/profile/"records.json")
        labels=[]
        detailed=[]
        for row in rows:
            q=byid[row["query_id"]]
            a=row["agent"]
            n=int(q["id"].rsplit("-",1)[1])
            assert a["status"]!="error"
            context_ids=set(a["model_context_ids"])
            context=a["model_context"]
            evidence=[]
            if q["answerable"]:
                for cid in context_ids:
                    c=chunks[cid]
                    if any(c["source_id"]==g["source_id"] and c["page"]==g["page"]
                           and norm(g["evidence"]) in norm(c["text"]) for g in q["gold"]):
                        assert norm(c["text"]) in norm(context)
                        assert norm(c["text"]) in pdf_pages[c["page"]]
                        evidence.append({"id":cid,"source_id":c["source_id"],"page":c["page"],"quote":c["text"]})
                assert evidence,"Context grade 2 must have checked complete source evidence"
            citation_reviews=[]
            for cid in a["citations"]:
                c=chunks[cid]
                present=cid in context_ids and c["text"] in context
                source_verified=norm(c["text"]) in pdf_pages[c["page"]]
                assert present and source_verified
                partial=n in (4,5)
                citation_reviews.append({"id":cid,"source_id":c["source_id"],"source":c["source"],
                    "page":c["page"],"quote":c["text"],"present_in_final_model_context":present,
                    "pdf_text_verified":source_verified,
                    "support_level":"partial" if partial else "full",
                    "supports_main_expected_answer":True,
                    "supports_full_attached_claim_bundle":not partial,
                    "citation_support":not partial,
                    "reason":REASONS[n] if partial else "Nguồn trong context hỗ trợ các khẳng định được gắn citation, đối chiếu đoạn PDF."})
            label={"query_id":q["id"],"citation_support":[c["citation_support"] for c in citation_reviews]}
            if q["answerable"]:label["answer_grade"]=GRADES[profile][n]
            else:
                assert a["status"]=="abstain" and not a["citations"]
                label["abstention_correct"]=True
            labels.append(label)
            detailed.append({"query_id":q["id"],"profile":profile,"split":"test","answerable":q["answerable"],
                "question":q["question"],"expected_answer":q["expected_answer"],
                "status":a["status"],"published_answer":a["answer"],"stop_reason":a["stop_reason"],
                "context_grade":2 if q["answerable"] else None,
                "context_reason":"Context cuối có đủ evidence và nguồn cho mọi điều kiện được hỏi; không suy chất lượng answer từ context." if q["answerable"] else
                                 "Không tính vào mẫu context của câu có đáp án; đối chiếu phạm vi corpus để chấm abstention riêng.",
                "context_evidence":evidence,"answer_grade":label.get("answer_grade"),
                "answer_reason":REASONS[n],"citation_reviews":citation_reviews,
                "abstention_correct":label.get("abstention_correct"),"tool_calls":a["search_count"],
                "trace_path":(RUN/profile/q["id"]/"agent_trace.json").relative_to(ROOT).as_posix(),
                "provenance":provenance})
        quality=aggregate(cases,[r["agent"] for r in rows],labels)
        context_grades=[r["context_grade"] for r in detailed if r["answerable"]]
        quality.update(profile=profile,split="test",context_grade_counts={str(g):context_grades.count(g) for g in [0,1,2]},
            context_grade_mean=sum(context_grades)/len(context_grades),
            context_grade_N=len(context_grades),
            search_count_distribution={str(i):sum(r["agent"]["search_count"]==i for r in rows) for i in range(3)},
            trace_source=RUN.relative_to(ROOT).as_posix(),
            abstention_note="Both missing-evidence cases truly refused without unsupported numeric claims; no failure counted as correct abstention.")
        write(OUT/(profile+"_reviews.json"),detailed)
        write(OUT/(profile+"_labels.json"),labels)
        write(OUT/(profile+"_summary.json"),quality)
        summaries.append(quality)
        all_reviews.extend(detailed)
    write(OUT/"summary.json",{"profiles":summaries,"provenance":provenance,
        "reviewed_case_runs":14,"context_answerable_case_runs":10,
        "published_citations_reviewed":sum(len(r["citation_reviews"]) for r in all_reviews),
        "input_hashes":{"freeze_sha256":hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
          "test_summary_sha256":hashlib.sha256((RUN/"summary.json").read_bytes()).hexdigest(),
          "pdf_sha256":hashlib.sha256(PDF.read_bytes()).hexdigest()},
        "no_api_calls":True,"frozen_pipeline_changed":False,
        "selection_changed_after_test":False,"student_confirmation":"pending"})
    lines=["# Đánh giá context và câu trả lời test — task 10\n\n",
           "Đọc đủ 7 câu test × 2 cấu hình, đối chiếu context thực gửi model, câu trả lời xuất bản, tất cả citation với PDF. Nhãn do **Codex hỗ trợ, chưa được học viên xác nhận**, không phải chấm mù độc lập. Không gọi API, không sửa pipeline/freeze hoặc cấu hình chọn.\n\n",
           "| Cấu hình | Context 0/1/2; mean | Grounded answer 0/1/2; mean | Citation hỗ trợ đầy đủ | Answer có citation | Tool use | Abstention đúng | Từ chối nhầm |\n",
           "|---|---|---|---|---|---|---|---|\n"]
    for s in summaries:
        g=s["grounded_answer"]
        frac=lambda x:str(x["n"])+"/"+str(x["N"])
        lines.append("| "+s["profile"]+" | 0/0/5; 2.00/2 | "+str(g["0"])+"/"+str(g["1"])+"/"+str(g["2"])+"; "+format(g["mean"],".2f")+"/2 | "+frac(s["citation_validity"])+" | "+frac(s["answer_citation_coverage"])+" | "+frac(s["tool_use"])+" | "+frac(s["abstention"])+" | "+frac(s["false_abstention"])+" |\n")
    lines+=["\nMẫu số grounded/context là 5 câu có đáp án mỗi cấu hình; abstention là 2 câu thiếu evidence; tool use là 7 case thành công. Tất cả case dùng 1 search. Không có lỗi hệ thống. Citation không có thì ghi 0/0 không áp dụng theo từng case, không coi là 100%.\n\n",
            "Citation partial có nguồn đúng và hỗ trợ ý chính nhưng không đủ toàn bộ khẳng định được gắn vào citation; bảng dùng full-support theo quy tắc không thêm claim thiếu căn cứ. Chi tiết giữ cả supports_main_expected_answer và supports_full_attached_claim_bundle để người chấm kiểm tra, không giấu phần hỗ trợ đúng.\n\n"]
    for profile in ["dense_4000","hybrid_6000"]:
        lines.append("## "+profile+"\n\n")
        for r in [r for r in all_reviews if r["profile"]==profile]:
            lines.append("- **"+r["query_id"]+"** — "+r["status"]+
                "; context="+str(r["context_grade"])+"; answer="+str(r["answer_grade"])+
                "; citation="+str(sum(c["citation_support"] for c in r["citation_reviews"]))+
                "/"+str(len(r["citation_reviews"]))+". "+r["answer_reason"]+"\n")
        lines.append("\n")
    lines+=["## Lỗi chính và giới hạn\n\n",
            "- hybrid_6000 d7-test-03: context đủ nhưng guard từ chối citation nhóm [id1, id2]; câu xuất bản là abstain nên answer grade 0, false abstention 1/5. Không chấm bản rejected như đáp án đã phát hành và không sửa guard sau khi xem test.\n",
            "- d7-test-04 của cả hai: đúng Different objectives nhưng thêm quan hệ nhân quả giữa hai lý do riêng trong sách. Chấm 1/2; citation hỗ trợ phần chính, chưa hỗ trợ trọn gói claim.\n",
            "- d7-test-05 của cả hai: đúng thiếu R&D/chậm đổi mới, nhưng nối ví dụ customer orientation thành hậu quả không được nguồn trích chứng minh. Chấm 1/2; giữ rõ phần đúng và phần suy diễn.\n",
            "- d7-test-06/07: cả hai thực sự từ chối, không nêu giá Cohealo hoặc ngân sách Walmart. Thiếu bằng chứng được kiểm tra trong corpus index, không suy từ một top-k rỗng.\n",
            "- Baseline có kết quả answer test tốt hơn cấu hình chọn ở lượt này; vẫn giữ hybrid_6000 vì đã chọn trên dev trước test. Kết quả chỉ 5+2 câu, một lượt model, không suy rộng hoặc đổi lựa chọn theo test.\n",
            "- Nhãn AI cần tác giả kiểm tra và xác nhận; đặc biệt các đánh giá partial/citation là phán xét nội dung, không phải một bộ đếm ID.\n\n",
            "Dữ liệu đầy đủ ở [summary.json](../artifacts/test_review/20261114T095337524594Z/summary.json) và hai file *_reviews.json; *_labels.json tương thích starter/agent_metrics.py. Mẫu null trong run gốc được giữ nguyên như output gốc; nhãn đã chấm nằm riêng, không viết lại lịch sử.\n\n",
            "Tái xuất review (cần pypdf theo scripts/requirements-analysis.txt): python scripts/review_test_outputs.py. Script chỉ tái tạo nhãn đã ghi nhận ở trên, không phải model tự chấm và không cần API key.\n"]
    (ROOT/"docs/TEST_REVIEW.md").write_text("".join(lines),encoding="utf-8")
    print(json.dumps(summaries,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
