# Đánh giá context và câu trả lời test — task 10

Đọc đủ 7 câu test × 2 cấu hình, đối chiếu context thực gửi model, câu trả lời xuất bản, tất cả citation với PDF. Nhãn do **Codex hỗ trợ, đã được học viên xác nhận**, không phải chấm mù độc lập. Không gọi API, không sửa pipeline/freeze hoặc cấu hình chọn.

| Cấu hình | Context 0/1/2; mean | Grounded answer 0/1/2; mean | Citation hỗ trợ đầy đủ | Answer có citation | Tool use | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| dense_4000 | 0/0/5; 2.00/2 | 0/2/3; 1.60/2 | 4/6 | 5/5 | 7/7 | 2/2 | 0/5 |
| hybrid_6000 | 0/0/5; 2.00/2 | 1/2/2; 1.20/2 | 2/4 | 4/4 | 7/7 | 2/2 | 1/5 |

Mẫu số grounded/context là 5 câu có đáp án mỗi cấu hình; abstention là 2 câu thiếu evidence; tool use là 7 case thành công. Tất cả case dùng 1 search. Không có lỗi hệ thống. Citation không có thì ghi 0/0 không áp dụng theo từng case, không coi là 100%.

Citation partial có nguồn đúng và hỗ trợ ý chính nhưng không đủ toàn bộ khẳng định được gắn vào citation; bảng dùng full-support theo quy tắc không thêm claim thiếu căn cứ. Chi tiết giữ cả supports_main_expected_answer và supports_full_attached_claim_bundle để người chấm kiểm tra, không giấu phần hỗ trợ đúng.

## dense_4000

- **d7-test-01** — answered; context=2; answer=2; citation=1/1. Đáp án nêu đủ automation, information generation và transformation/routines; text trang PDF 62 và citation hỗ trợ đủ ba ý.
- **d7-test-02** — answered; context=2; answer=2; citation=1/1. Đáp án đúng hỗ trợ chức năng kinh doanh cụ thể và tăng hiệu quả từng phòng ban; các ví dụ accounting/finance/operations/marketing/HR có ở trang 63.
- **d7-test-03** — answered; context=2; answer=2; citation=2/2. Dense nêu đúng tích hợp IT với strategy/mission/objectives và vai trò đối tác chiến lược, giao tiếp; hai đoạn trang 65 và 66 hỗ trợ. Hybrid xuất bản lời từ chối vì citation nhóm [id1, id2] bị guard loại; chấm câu trả lời xuất bản 0 dù bản rejected có ý đúng.
- **d7-test-04** — answered; context=2; answer=1; citation=0/1. Đúng ý chính Different objectives. Tuy nhiên đáp án thêm quan hệ nhân quả 'sự khác biệt này dẫn đến thiếu hiểu biết về chuyên môn'. Trang 66 liệt kê Different objectives và Lack of expertise awareness như các nguyên nhân riêng, không thiết lập quan hệ nhân quả đó; chấm đúng một phần 1/2.
- **d7-test-05** — answered; context=2; answer=1; citation=0/1. Đúng nguy cơ thiếu R&D và chậm đổi mới. Nhưng đáp án thêm suy luận mất lợi thế cạnh tranh dài hạn và ví dụ không đầu tư tùy chỉnh/hỗ trợ sẽ tụt hậu. Đoạn trích trang 67 chỉ mở tình huống chuyển sang customer orientation; phần nối trang 68 nói chi phí ban đầu/benefits, không chứng minh đầy đủ ví dụ kết luận của model; chấm 1/2.
- **d7-test-06** — abstain; context=None; answer=None; citation=0/0. Corpus index chỉ có mô tả chức năng/case Cohealo (trang 70–71), không có giá thuê bao tháng Clinical năm 2025. Đáp án xuất bản thực sự từ chối, không thêm giá hay khẳng định suy đoán.
- **d7-test-07** — abstain; context=None; answer=None; citation=0/0. Đoạn Walmart trang 67 minh họa cost leadership, không có ngân sách IT năm 2025. Đáp án xuất bản từ chối, không nêu con số ngoài nguồn.

## hybrid_6000

- **d7-test-01** — answered; context=2; answer=2; citation=1/1. Đáp án nêu đủ automation, information generation và transformation/routines; text trang PDF 62 và citation hỗ trợ đủ ba ý.
- **d7-test-02** — answered; context=2; answer=2; citation=1/1. Đáp án đúng hỗ trợ chức năng kinh doanh cụ thể và tăng hiệu quả từng phòng ban; các ví dụ accounting/finance/operations/marketing/HR có ở trang 63.
- **d7-test-03** — abstain; context=2; answer=0; citation=0/0. Dense nêu đúng tích hợp IT với strategy/mission/objectives và vai trò đối tác chiến lược, giao tiếp; hai đoạn trang 65 và 66 hỗ trợ. Hybrid xuất bản lời từ chối vì citation nhóm [id1, id2] bị guard loại; chấm câu trả lời xuất bản 0 dù bản rejected có ý đúng.
- **d7-test-04** — answered; context=2; answer=1; citation=0/1. Đúng ý chính Different objectives. Tuy nhiên đáp án thêm quan hệ nhân quả 'sự khác biệt này dẫn đến thiếu hiểu biết về chuyên môn'. Trang 66 liệt kê Different objectives và Lack of expertise awareness như các nguyên nhân riêng, không thiết lập quan hệ nhân quả đó; chấm đúng một phần 1/2.
- **d7-test-05** — answered; context=2; answer=1; citation=0/1. Đúng nguy cơ thiếu R&D và chậm đổi mới. Nhưng đáp án thêm suy luận mất lợi thế cạnh tranh dài hạn và ví dụ không đầu tư tùy chỉnh/hỗ trợ sẽ tụt hậu. Đoạn trích trang 67 chỉ mở tình huống chuyển sang customer orientation; phần nối trang 68 nói chi phí ban đầu/benefits, không chứng minh đầy đủ ví dụ kết luận của model; chấm 1/2.
- **d7-test-06** — abstain; context=None; answer=None; citation=0/0. Corpus index chỉ có mô tả chức năng/case Cohealo (trang 70–71), không có giá thuê bao tháng Clinical năm 2025. Đáp án xuất bản thực sự từ chối, không thêm giá hay khẳng định suy đoán.
- **d7-test-07** — abstain; context=None; answer=None; citation=0/0. Đoạn Walmart trang 67 minh họa cost leadership, không có ngân sách IT năm 2025. Đáp án xuất bản từ chối, không nêu con số ngoài nguồn.

## Lỗi chính và giới hạn

- hybrid_6000 d7-test-03: context đủ nhưng guard từ chối citation nhóm [id1, id2]; câu xuất bản là abstain nên answer grade 0, false abstention 1/5. Không chấm bản rejected như đáp án đã phát hành và không sửa guard sau khi xem test.
- d7-test-04 của cả hai: đúng Different objectives nhưng thêm quan hệ nhân quả giữa hai lý do riêng trong sách. Chấm 1/2; citation hỗ trợ phần chính, chưa hỗ trợ trọn gói claim.
- d7-test-05 của cả hai: đúng thiếu R&D/chậm đổi mới, nhưng nối ví dụ customer orientation thành hậu quả không được nguồn trích chứng minh. Chấm 1/2; giữ rõ phần đúng và phần suy diễn.
- d7-test-06/07: cả hai thực sự từ chối, không nêu giá Cohealo hoặc ngân sách Walmart. Thiếu bằng chứng được kiểm tra trong corpus index, không suy từ một top-k rỗng.
- Baseline có kết quả answer test tốt hơn cấu hình chọn ở lượt này; vẫn giữ hybrid_6000 vì đã chọn trên dev trước test. Kết quả chỉ 5+2 câu, một lượt model, không suy rộng hoặc đổi lựa chọn theo test.
- Nhãn AI đã được học viên xác nhận; đặc biệt các đánh giá partial/citation là phán xét nội dung, không phải một bộ đếm ID.

Dữ liệu đầy đủ ở [summary.json](../artifacts/test_review/20261114T095337524594Z/summary.json) và hai file *_reviews.json; *_labels.json tương thích starter/agent_metrics.py. Mẫu null trong run gốc được giữ nguyên như output gốc; nhãn đã chấm nằm riêng, không viết lại lịch sử.

Tái xuất review (cần pypdf theo scripts/requirements-analysis.txt): python scripts/review_test_outputs.py. Script chỉ tái tạo nhãn đã ghi nhận ở trên, không phải model tự chấm và không cần API key.
