# Kết quả dev sau chạy bù lỗi

Run gốc: 20261114T092856910861Z. Retry: 20261114T093849461754Z. Đã chạy bù đúng 19 case lỗi một lần sau khi học viên bổ sung credit/limit; giữ nguyên model, prompt, tool schema, cấu hình và benchmark. Không chạy lại 49 case đã thành công, không chọn đáp án đẹp hơn từ nhiều lần thử. Bộ hợp nhất có 68 case, 0 lỗi hệ thống; chưa chạy test.

| Profile | Hit@1 query gốc | Hit@3 query gốc | Context Evidence Rate agent (literal) | Lỗi còn lại | Query median ms | Agent median s | Cost case hiệu lực USD | Cost đã biết mọi attempt USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dense_4000 | 8/15 | 13/15 | 13/15 | 0 | 900.698 | 4.659 | 0.01967950 | 0.01989278 |
| lexical_4000 | 7/15 | 11/15 | 11/15 | 0 | 0.355 | 3.988 | 0.01772680 | 0.01879560 |
| hybrid_4000 | 8/15 | 12/15 | 12/15 | 0 | 869.045 | 4.739 | 0.02028616 | 0.02028972 |
| hybrid_6000 | 8/15 | 12/15 | 14/15 | 0 | 889.794 | 4.804 | 0.02417208 | 0.02482588 |

## Phạm vi và mẫu số

- Mỗi profile chạy 17 câu dev: 15 có đáp án và 2 thiếu evidence. Hit/context chỉ dùng mẫu số 15, không thêm các câu thiếu bằng chứng.
- Ranking query gốc trong bảng lấy từ run gốc; raw query được kiểm tra lại trong retry nhưng không thay ranking gốc trong phép so sánh. Context Evidence Rate lấy context thực sự ghi trong request model của attempt hiệu lực, không dùng context dự kiến.
- Đây là literal evidence scoring; chưa phải nhãn grounded answer/citation đúng về nội dung. Trạng thái answered/abstain không được tự coi là trả lời đúng/từ chối đúng. Chưa chọn cấu hình thắng vì còn bước chấm chất lượng câu trả lời và phân tích lỗi dev.
- 4000/6000 hybrid vẫn cùng retriever; khác context budget. CER cao hơn không đồng nghĩa câu trả lời đúng hơn hoặc là kết luận trên test.

## Chi phí và thời gian

- Tổng subtotal chi phí benchmark provider trả về, gồm run gốc và retry: **$0.08380398**. Tổng này không bao gồm smoke/integration trước benchmark hoặc chi phí DAY06.
- Cột cost case hiệu lực chỉ tính 68 case được dùng cho metrics, loại attempt lỗi đã thay. Cột cost mọi attempt cộng cả kết quả lỗi cũ và retry, kể cả embedding gọi lại. Không cộng hai cột thành tổng mới.
- 18 request lỗi 402 cũ không có usage/cost nên tổng đối soát toàn bộ vẫn chưa biết chính xác (null); không tự giả định request lỗi miễn phí. Những phần cost có phản hồi được cộng đúng theo usage.
- Latency là một lần đo, profile chạy đồng thời; bộ hợp nhất gồm 49 case gốc và 19 case ở thời điểm retry. Query median dùng raw gốc; agent median dùng attempt hiệu lực. Không coi là phép đo latency cô lập hay kiểm định thống kê.

## Artifact và tái lập

- effective_records.json: 68 kết quả hợp nhất, kèm nguồn attempt, ranking gốc và trace agent.
- summary.json: metrics, billing_all_attempts, số retry và lỗi còn lại.
- comparison.csv: bảng máy đọc; run_manifest.json: 19 case được phép retry và xác nhận model/prompt/settings không đổi.
- Các thư mục profile/query chứa trace retry riêng. Toàn bộ lỗi gốc và trace gốc ở artifacts/dev_benchmark/20261114T092856910861Z vẫn giữ nguyên.
- scripts/retry_dev_errors.py chỉ dành cho 19 lỗi của run gốc; không chạy lại lệnh này nếu không chủ ý tạo thêm 19 attempt có phí.
