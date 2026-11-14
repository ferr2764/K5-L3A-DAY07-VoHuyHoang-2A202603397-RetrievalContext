# Benchmark DAY07 — Foundations of Information Systems

Bộ câu hỏi được chuẩn bị trước thử nghiệm DAY07, dùng cùng 162 chunk B và index DAY06, model embedding openai/text-embedding-3-small (1.536 chiều). Corpus gồm 34 trang nội dung trong phạm vi trang PDF vật lý 30–72. Số trang gold là số PDF từ 1, không phải số in trong sách.

| Split | Có đáp án | Thiếu bằng chứng | Tổng |
|---|---:|---:|---:|
| dev | 15 | 2 | 17 |
| test | 5 | 2 | 7 |
| Tổng | 20 | 4 | 24 |

## Các file

- [questions.json](questions.json): đủ 24 câu, đáp án/hành vi mong đợi, split, gold, filter và lý do thiếu bằng chứng.
- [answerable_questions.json](answerable_questions.json): 20 câu có đáp án cho baseline retrieval, loại 4 câu không đủ evidence khỏi mẫu số.
- [cases.json](cases.json): metadata 24 case cho script tổng hợp agent; không chứa gold.
- [validation.json](validation.json): hash PDF/chunks/benchmark, kiểm chứng gold trên PDF và chunk, phạm vi kiểm tra câu thiếu bằng chứng.
- [../../scripts/build_benchmark.py](../../scripts/build_benchmark.py): tái tạo bộ câu hỏi và kiểm chứng, không gọi API.

## Nguồn và cách chia

Dev d7-dev-01–15 dùng 15 câu dev DAY06 thuộc mục 1.2, 1.3, 2.1. Câu d7-dev-06 được thu hẹp thành vai trò câu hỏi Where? của Zachman để evidence nằm trọn trong một chunk. Không đổi chunk/index. Evidence lưu nguyên đoạn text có xuống dòng trong chunk để tương thích phép khớp của baseline; đối chiếu PDF bằng Unicode NFC và gộp whitespace.

Năm câu test có đáp án là các mục tiêu trả lời mới thuộc mục 2.2:

| ID | Nội dung |
|---|---|
| d7-test-01 | Ba cách IT tạo giá trị |
| d7-test-02 | Vai trò của FAIS |
| d7-test-03 | Business–IT alignment |
| d7-test-04 | Khác biệt mục tiêu business/IT |
| d7-test-05 | Đánh đổi cost leadership với R&D/đổi mới |

Không tái dùng 5 câu test hoặc 2 câu dự phòng DAY06. Tuy nhiên vẫn cùng sách/index và một số trang từng được nhìn thấy qua retrieval DAY06; đây là test mới về câu hỏi và mục tiêu trả lời, không phải corpus hoàn toàn mới. Test tập trung mục 2.2 nên tính đại diện hạn chế. Gold được đọc để xây benchmark; từ đây chỉ dùng dev để chọn cấu hình.

Không thay câu hỏi/gold hoặc đổi split theo kết quả test. Nếu dùng test để tinh chỉnh, công bố và tạo test mới. Trước lần thử đầu tiên, học viên nên đọc xác nhận tính đúng của bộ câu hỏi.

## Bốn câu thiếu bằng chứng

| ID | Split | Thông tin không được corpus cung cấp |
|---|---|---|
| d7-dev-16 | dev | Số ngày VinUni phải giữ log hệ thống sinh viên |
| d7-dev-17 | dev | Lệ phí thi SFIA tại Việt Nam năm 2026 |
| d7-test-06 | test | Giá thuê bao tháng Cohealo + Clinical năm 2025 |
| d7-test-07 | test | Chi tiêu IT chính xác của Walmart năm 2025 |

Phạm vi kiểm chứng là toàn bộ text được index của 34 trang/162 chunk, kết hợp đọc đoạn chủ đề liên quan và tìm các thực thể, năm, đơn vị. Không kết luận thiếu thông tin chỉ vì top-k rỗng hoặc một từ khóa không xuất hiện; không tuyên bố toàn bộ sách 497 trang hay thế giới bên ngoài không có thông tin này.

Agent cần tìm rồi nêu không đủ bằng chứng để trả lời con số cụ thể, không suy đoán hoặc lấy kiến thức ngoài làm đáp án. Chỉ được chấm abstention đúng nếu câu trả lời thực sự từ chối và không kèm khẳng định vô căn cứ.

## Filter, citation và cách chấm

Các câu có filter là d7-dev-03, d7-dev-09, d7-test-01, d7-test-03. Phạm vi mục được nêu sẵn trong query; không suy ra filter từ gold. Với câu khác, filter là null.

Gold là danh sách bằng chứng thay thế; chấp nhận bất kỳ phần tử hợp lệ, không bắt buộc đồng thời tất cả. Tất cả 20 câu có đáp án đều có evidence đủ trả lời nằm trong một chunk của index hiện có. Bằng chứng tương đương khác được phép sau đối chiếu nguồn và ghi quyết định áp dụng thống nhất cho mọi phương pháp.

- Hit@1 / Evidence Hit@3: chỉ tính câu có đáp án; báo n/N theo split, cùng cutoff cho mọi phương pháp.
- Context Evidence Rate: có đủ bằng chứng hợp lệ trong context cuối; không suy từ top-3 nếu context bị budget loại bỏ.
- Context 0–2, grounded answer 0–2, citation hỗ trợ nội dung và abstention cần nhãn/lý do từng case.
- Agent/controller chỉ nhận question và filter phù hợp; không nhận gold, expected_answer, answerable, absence_reason hoặc các nhãn chấm.
- cases.json dùng cho tổng hợp đánh giá, không tự động đưa nguyên case vào prompt.

## Cách dùng

Từ thư mục gốc DAY07, chỉ để kiểm chứng/tái tạo bộ đã soạn (không chạy retrieval):

~~~powershell
python scripts/build_benchmark.py
~~~

Script cần PDF và benchmark DAY06 trong thư mục cùng cấp như đường dẫn ghi ở đầu script, và chunk tại starter/data/day6/chunks.json. Nó sẽ ghi lại các JSON benchmark; chỉ chạy có chủ ý sau khi chốt phiên bản. Nếu chuyển repo sang máy khác, giữ hai repo cùng cấp hoặc chỉnh đường dẫn PDF/DAY06 trong script và ghi nhận thay đổi nguồn.

Khi triển khai bước chạy lexical dev, dùng answerable_questions.json thay cho questions.json vì baseline mẫu yêu cầu mỗi câu có gold không rỗng. Khi chạy agent, dùng toàn bộ 24 câu và chọn đúng split; tách nhãn/gold khỏi dữ liệu gửi model.

Kết quả từ việc dựng benchmark chỉ là kiểm chứng nguồn. Chưa chạy benchmark retrieval, agent, hoặc tạo điểm chất lượng.
