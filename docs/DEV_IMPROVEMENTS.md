# Hai thí nghiệm cải thiện và phân tích lỗi dev

Các cấu hình đã chốt trước dev và đã chạy thật ở bước 7; bước 8 này phân tích kết quả đã lưu, không gọi API lại hoặc thay câu trả lời. Nhãn nội dung do Codex hỗ trợ đối chiếu PDF, **đã được học viên xác nhận**. Phân tích được thực hiện trên dev trước khi chọn; cấu hình cuối cùng hybrid_6000 và kết quả test được trình bày trong TEST_BENCHMARK.md.

| Thí nghiệm | Trước → sau | Giả thuyết | Hit@1 | Hit@3 | Context Evidence Rate |
|---|---|---|---|---|---|
| Cải thiện 1 | dense_4000 → hybrid_4000 | RRF kết hợp lexical và semantic | 8/15 → 8/15 | 13/15 → 12/15 | 13/15 → 12/15 |
| Cải thiện 2 | hybrid_4000 → hybrid_6000 | Tăng budget để giữ chunk xếp thấp | 8/15 → 8/15 | 12/15 → 12/15 | 12/15 → 14/15 |

RRF là một phương pháp mới và đồng thời một cấu hình thử cải thiện; kết quả aggregate bị giảm vẫn là thí nghiệm hợp lệ. Cải thiện 2 chỉ thay budget; hai lỗi minh họa dưới đây có cùng query agent và cùng toàn bộ thứ tự candidate, giúp đối chiếu trực tiếp tác động của đóng gói context.

## d7-dev-05 — sfia_level5_budget

- Trang PDF: 32. Đáp án: Level 5 — Ensure and Advise.
- Nguyên nhân: Gold chunk at agent hybrid rank 6 is 1046 chars including header; 4000-budget remaining 160 chars so it is skipped. Model confuses Level 6 with expected Level 5.
- Giả thuyết: Keep same ranking and increase budget to fit the whole SFIA level-definition chunk.
- Trước (hybrid_4000): Theo SFIA, cấp 6 (Initiate and Influence) cho phép nhận định hướng rộng và tự khởi xướng công việc được cho là cần thực hiện. Ở cấp này, nhân viên đóng vai trò trung tâm trong việc thiết lập mục tiêu của tổ chức và phân công trách nhiệm cho cấp dưới, thực hiện các nhiệm vụ phức tạp và đưa ra các quyết định ảnh hưởng trực tiếp đến hiệu suất và mục tiêu của tổ chức [8087e20413e3d0e51298e5d866ae48d172b1aebca5f8c7ea13efd96281cc4dd7].
- Sau (hybrid_6000): Theo SFIA, cấp 5 (Ensure and Advise) cho phép nhân viên nhận định hướng rộng và có khả năng tự khởi xướng công việc mà họ cho là cần thực hiện. Ở cấp này, nhân viên nhận được sự chỉ đạo rộng rãi, có nhiều quyền tự chủ, bao gồm khả năng tự khởi xướng công việc mà họ nghĩ là cần thiết. Công việc của họ thường phức tạp và là một phần quan trọng trong kế hoạch chiến lược của tổ chức [1935f2d34d89b7b6cb1e4b5b297680dbd6e72ed33e1d874ac09132ea0c5b6dde].
- Kết quả: Context evidence false -> true; selected-case answer grade 0 -> 2; no claim about all dev answers.
- Trace: [trước](../artifacts/dev_benchmark/20261114T092856910861Z/hybrid_4000/d7-dev-05/agent_trace.json), [sau](../artifacts/dev_benchmark/20261114T092856910861Z/hybrid_6000/d7-dev-05/agent_trace.json).

## d7-dev-11 — velocity_budget_unsupported_citation

- Trang PDF: 56. Đáp án: Velocity.
- Nguyên nhân: Gold Velocity chunk at hybrid rank 6 is 932 chars; 4000-budget remaining 191 chars skips it. Answer names Velocity but cites a chunk defining Volume/Variety, not the requested relationship.
- Giả thuyết: Increase context budget while holding the hybrid ranking fixed to retain the explicit Velocity definition.
- Trước (hybrid_4000): Nếu dữ liệu được sinh và thu thập nhanh đến mức cần xử lý thời gian thực, đó là thuộc chiều "Velocity" (tốc độ) của big data. Chiều này đề cập đến tốc độ dữ liệu được tạo ra và xử lý để đáp ứng các yêu cầu thời gian thực hoặc gần thời gian thực trong các ứng dụng vận hành và ra quyết định nhanh chóng [eab422a8084144f9dab0a4517a0224040455e5537e09bbf3dc91497f382a0245].
- Sau (hybrid_6000): Chiều của big data liên quan đến việc dữ liệu được sinh và thu thập nhanh đến mức cần xử lý thời gian thực là chiều "Velocity" (tốc độ). Velocity đặc trưng cho tốc độ nhanh chóng mà dữ liệu được tạo ra và thu thập, đòi hỏi phải xử lý ngay lập tức hoặc gần như thời gian thực để có thể phân tích và đưa ra các quyết định kịp thời. Ví dụ, trong các sự kiện có lưu lượng truy cập cao như các đợt bán hàng trực tuyến nhanh, dữ liệu clickstream liên tục được thu thập và cần phân tích nhanh để cung cấp các đề xuất và thông tin phù hợp cho người dùng trong môi trường số động này [dee1475be0defeb746d717f20ee940ba925656b19620983335f9c4d15c80a65c].
- Kết quả: Context evidence false -> true; selected-case grounded grade 0 -> 2; original Vietnamese-query Hit@3 remains a miss.
- Trace: [trước](../artifacts/dev_benchmark/20261114T092856910861Z/hybrid_4000/d7-dev-11/agent_trace.json), [sau](../artifacts/dev_retries/20261114T093849461754Z/hybrid_6000/d7-dev-11/agent_trace.json).

## d7-dev-04 — sfia_level3_rrf_regression

- Trang PDF: 32. Đáp án: Level 3 — Apply.
- Nguyên nhân: Original dense ranks correct Level-3 chunk 3rd; RRF moves it to 4th. Agent rewritten query moves target to dense rank 7/hybrid rank 8; context budgets both skip it.
- Giả thuyết: RRF might preserve useful exact SFIA terms; larger context might recover lower-ranked evidence.
- Trước (dense_4000): Không đủ bằng chứng trong tài liệu để trả lời.
- Sau (hybrid_6000): Theo SFIA, nhân viên nhận giám sát tổng quát, có thêm tự chủ, công việc có thể không thường lệ và có thể giám sát người khác thuộc cấp độ 5. Cấp độ này là "Ensure, Advise" (Đảm bảo, Tư vấn), trong đó nhân viên có trách nhiệm giám sát tổng quát, có mức độ tự chủ cao hơn và công việc có thể không theo quy trình thường lệ, đồng thời có thể giám sát người khác. Đây là cấp độ cao hơn so với các cấp độ đầu như "Follow" (theo dõi) hay "Assist" (hỗ trợ) và thấp hơn các cấp độ như "Initiate and Influence" (Khởi xướng và Ảnh hưởng) hoặc "Set Strategy, Inspire, and Mobilize" (Đặt chiến lược, Truyền cảm hứng và Huy động) dành cho các nhà lãnh đạo cấp cao [6f16c7ac104d147cb7ca391fd5bed7627b0ea254727b71f73c25d577d1a2c0f8].
- Kết quả: Not fixed; raw Hit@3 true -> false and answer remains grade 0. Do not equate answered with improvement.
- Trace: [trước](../artifacts/dev_benchmark/20261114T092856910861Z/dense_4000/d7-dev-04/agent_trace.json), [sau](../artifacts/dev_benchmark/20261114T092856910861Z/hybrid_6000/d7-dev-04/agent_trace.json).

## Chi phí, đánh đổi và giới hạn

- dense_4000: cost của case hiệu lực $0.01967950; median agent 4.659 giây.
- hybrid_4000: cost của case hiệu lực $0.02028616; median agent 4.739 giây.
- hybrid_6000: cost của case hiệu lực $0.02417208; median agent 4.804 giây.

Tổng cost benchmark đã biết gồm cả attempt gốc và retry là $0.08380398; không cộng thêm các cost case hiệu lực vào tổng này. Chi phí request lỗi không có usage vẫn chưa đối soát. Latency là phép đo chạy đồng thời và ở hai thời điểm, không coi là thử nghiệm cô lập.

Hai lỗi được sửa theo evidence/đáp án không chứng minh mọi câu đều tốt hơn. d7-dev-04 vẫn sai; một số case MDM bị từ chối do định dạng citation nhóm. Chưa sửa guard hay rerun các case đó trong bước này để tránh trộn pipeline khác vào kết quả đã đo. Nếu sửa tiếp, tạo config/run mới trên dev và ghi thay đổi, giữ nguyên test.

Dữ liệu máy đọc: [analysis.json](../artifacts/dev_improvements/analysis.json). Tái tạo phân tích không gọi API: python scripts/analyze_dev_improvements.py. Các giá trị answer grade trong file chỉ thuộc các case đã đọc, không tự điền cho toàn bộ dev. Cần chấm đủ grounded answers, citation và abstention trước khi chọn cấu hình theo protocol.

## Dependency để tái đối chiếu PDF

Script phân tích cần pypdf; môi trường DAY07 ban đầu chỉ có SDK/API dependencies. Nếu thiếu, cài thêm dependency phân tích riêng (không thay requirements gốc):

~~~powershell
python -m pip install -r scripts/requirements-analysis.txt
python scripts/analyze_dev_improvements.py
~~~
