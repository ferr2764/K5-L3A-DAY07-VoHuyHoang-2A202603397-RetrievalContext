# Chốt cấu hình và chạy test — task 9

Đã chốt hybrid_6000 bằng dev, trước khi chạy test; baseline dense_4000. Grounded answer mean dev theo review có hỗ trợ AI: dense/lexical 1,3333/2; hybrid_4000 1,4667/2; hybrid_6000 1,6000/2. Các profile đều không lỗi sau retry, abstention dev 2/2; thứ tự ưu tiên chọn được giữ từ protocol. Nhãn dev do Codex đọc nguồn/trace, đã được học viên xác nhận, không coi là đánh giá mù độc lập.

- [Nhãn 68 case dev](../artifacts/selection/20261114T095320637430Z/dev_reviews.json).
- [Điểm và lý do chọn](../artifacts/selection/20261114T095320637430Z/dev_selection.json).
- [Freeze trước test](../artifacts/selection/20261114T095320637430Z/freeze.json).
- [Bảng test](../artifacts/test_benchmark/20261114T095337524594Z/comparison.md), [summary](../artifacts/test_benchmark/20261114T095337524594Z/summary.json).

Freeze giữ model/generation settings, prompt/tool hash, hash benchmark/chunks và code runtime/retrieval/context/evaluator. Protocol gốc vẫn giữ selected_configuration=null như bản quy tắc trước thử nghiệm; cấu hình đã chọn được ghi ở freeze riêng, không sửa lịch sử protocol.

Runner mới: scripts/run_test_benchmark.py. Nó chỉ đọc 7 câu split=test sau khi kiểm tra freeze, chạy đúng baseline và cấu hình chọn, giữ lỗi thật, checkpoint từng case và lưu chi phí/token. Đã chạy test một lần với 14 case, 0 lỗi; không cần gọi API lại để đọc kết quả. Chạy lại command tạo run mới và có phí, không biến test đã đọc thành holdout mới.

Không chạy lại script select_dev_configuration.py để tạo một freeze có thời gian sau test rồi trình bày như freeze trước lượt test này. Dùng đúng artifact freeze được dẫn ở trên. Chưa chỉnh agent theo test; bước tiếp là chấm nội dung và citation test (task 10), không tune pipeline.

## Đánh giá nội dung sau test

Task 10 đã có [TEST_REVIEW.md](TEST_REVIEW.md) và [nhãn/summary](../artifacts/test_review/20261114T095337524594Z/summary.json). Nhãn do Codex hỗ trợ, đã được học viên xác nhận. Pipeline/freeze không thay đổi; các ghi chú pending ở run gốc phản ánh thời điểm chạy, không có nghĩa review riêng chưa được thực hiện.
