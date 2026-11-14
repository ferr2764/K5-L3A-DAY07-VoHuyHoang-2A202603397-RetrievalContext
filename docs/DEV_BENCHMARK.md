# Cập nhật sau khi chạy bù

Đã chạy bù đúng 19 case lỗi với cấu hình không đổi; bộ hợp nhất có **68 case, 0 lỗi hệ thống**, chưa chạy test. Kết quả mới: [comparison](../artifacts/dev_retries/20261114T093849461754Z/comparison.md), [summary](../artifacts/dev_retries/20261114T093849461754Z/summary.json). Chi phí benchmark provider đã trả về gồm cả run gốc/retry: **$0.08380398**, chưa phải tổng đối soát tuyệt đối của các request lỗi không có usage.

Các đoạn dưới mô tả run đầu tiên và được giữ làm lịch sử sự cố; dùng bảng hợp nhất ở trên cho so sánh hiện tại.

# Chạy và so sánh trên dev — task 7

Kết quả: [comparison.md](../artifacts/dev_benchmark/20261114T092856910861Z/comparison.md), [summary.json](../artifacts/dev_benchmark/20261114T092856910861Z/summary.json), [comparison.csv](../artifacts/dev_benchmark/20261114T092856910861Z/comparison.csv).

Code: [runner](../scripts/run_dev_benchmark.py), [evaluator và cost instrumentation](../src/dev_evaluation.py). Chỉ chạy dev, 15 câu answerable + 2 câu thiếu evidence trên 4 profile, cùng model/prompt/corpus/filter.

Đã thử 68 lượt agent thật; 18 lỗi HTTP 402 và 1 lỗi tool schema. Ranking query gốc đủ; so sánh chất lượng agent còn bị ảnh hưởng bởi lỗi provider. Chưa chạy test hoặc chọn cấu hình. Các nhãn đánh giá nội dung để trống có chủ ý.

Kiểm tra offline:

~~~powershell
python -B -m unittest tests.test_dev_evaluation -v
~~~

Không chạy discovery toàn bộ test một cách vô ý: tests/test_dense.py hiện gọi API khi import.
