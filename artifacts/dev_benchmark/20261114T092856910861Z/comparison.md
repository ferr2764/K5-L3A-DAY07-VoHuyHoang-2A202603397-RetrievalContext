# So sánh dev DAY07

Run 20261114T092856910861Z: 17 câu dev × 4 profile, 68 lượt đã thử, 49 lượt agent thành công và 19 lỗi. Không chạy test. Model openai/gpt-4.1-mini, cùng prompt/tools và snapshot 162 chunk.

| Profile | Hit@1 gốc | Hit@3 gốc | Context Evidence Rate agent (literal) | Agent thành công | Lỗi | Query median ms | Agent median s | Cost đã biết USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dense_4000 | 8/15 | 13/15 | 9/15 | 11/17 | 6 | 900.698 | 4.211 | 0.01286278 |
| lexical_4000 | 7/15 | 11/15 | 11/15 | 16/17 | 1 | 0.355 | 3.858 | 0.01764520 |
| hybrid_4000 | 8/15 | 12/15 | 9/15 | 12/17 | 5 | 869.045 | 4.443 | 0.01447708 |
| hybrid_6000 | 8/15 | 12/15 | 9/15 | 10/17 | 7 | 889.794 | 4.470 | 0.01531868 |

## Diễn giải và giới hạn

- Ranking query gốc dùng cùng cutoff và mẫu số 15 câu có đáp án. Hai câu thiếu evidence mỗi profile không nằm trong mẫu số retrieval/context.
- Context Evidence Rate đo evidence trong context cuối được ghi trong request model, không thay bằng context dự kiến. Lỗi là miss trên mẫu số 15; nhiều lỗi 402 khiến các profile không có điều kiện provider ổn định như nhau. Chưa chọn cấu hình thắng.
- Dense query gốc Hit@3 13/15, TF-IDF 11/15, hybrid 12/15. Hybrid 4000/6000 có cùng retriever nên ranking query gốc bằng nhau.
- Tổng cost từ usage có phản hồi: **$0.06030374**. Request lỗi không có usage nên tổng đối soát còn null, không coi là 0. Lexical có cost đo đủ $0.01764520. Đây là chi phí DAY07, khác $0.0018 của DAY06.
- Embedding token/cost thực được ghi theo từng request. Mỗi profile có cache riêng; raw query chạy trước agent, cache hit được log. Không chia sẻ cache giữa profile. Bốn worker chạy đồng thời nên latency không phải đo cô lập.
- HTTP 402: dense 6, hybrid_4000 5, hybrid_6000 7. Lexical d7-dev-11 có lỗi InvalidToolSchema. Không loại case, không fallback, không đổi model/max_tokens giữa lượt để né lỗi.
- Nhãn grounded answer, citation support, abstention đúng và context 0–2 vẫn để null để đối chiếu nội dung sau. Answered và citation ID đúng chưa chứng minh câu trả lời đúng.

## Artifact và chạy lại

Mỗi profile có summary.json và records.json. Mỗi query có original_query.json, agent_trace.json, evaluation.json, embedding_usage.json, context_selection.json, context.txt, model_context.txt. Run manifest ghi model, prompt/tools hash, protocol/chunk/benchmark hash, phiên bản SDK và cache policy.

Chạy từ gốc DAY07:

~~~powershell
python -X utf8 scripts/run_dev_benchmark.py --workers 4
~~~

Lệnh này chạy lại toàn bộ dev và phát sinh phí mới. Nếu chạy bù lỗi, cần kiểm tra credit/limit OpenRouter trước, giữ nguyên model/prompt/cấu hình và lưu attempt mới riêng; không chọn đáp án đẹp hơn từ nhiều lần thử. Không dùng test để né lỗi.
