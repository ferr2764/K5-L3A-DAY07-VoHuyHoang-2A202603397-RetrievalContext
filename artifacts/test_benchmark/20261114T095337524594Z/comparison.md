# Test sau khi chốt cấu hình trên dev

Cấu hình chọn: hybrid_6000; baseline: dense_4000. Freeze được tạo trước test tại [freeze.json](../../selection/20261114T095320637430Z/freeze.json). Model openai/gpt-4.1-mini, cùng prompt/tools; chỉ khác phương pháp và budget theo profile đã chốt. Test gồm 5 câu có đáp án và 2 thiếu evidence, chạy cả hai cấu hình: 14 case, 0 lỗi hệ thống.

| Profile | Hit@1 query gốc | Hit@3 query gốc | Context Evidence Rate agent (literal) | Answered / abstain / error | Median query ms | Median agent s | Cost test USD |
|---|---:|---:|---:|---|---:|---:|---:|
| dense_4000 | 3/5 | 4/5 | 5/5 | 5 / 2 / 0 | 892.140 | 4.413 | 0.00808006 |
| hybrid_6000 | 1/5 | 4/5 | 5/5 | 4 / 3 / 0 | 882.302 | 4.531 | 0.00930324 |

## Đọc kết quả

- Các metric ranking/context là literal theo cùng gold và cutoff; không cộng 2 câu thiếu bằng chứng vào mẫu số 5.
- CER 5/5 là đủ literal evidence trong context cuối đã gửi model, không phải độ chính xác trả lời. Hybrid từ chối một câu có đáp án, nên không suy chất lượng answer từ CER.
- Có trace đầy đủ cho tất cả 14 case; nếu có timeout/lỗi cũng phải lưu và tính đúng mẫu số. Lần test này không phát sinh lỗi hệ thống.
- Tổng cost test có usage provider: **$0.01738330**; tách khỏi dev và smoke. Không tính $0.0018 DAY06 thành cost DAY07.
- Chưa chấm semantic answer/context 0–2 hoặc từng citation test trong bước này. Các file evaluation.json giữ manual_review=null cho task 10.
- Không sửa query, model, prompt, budget, filter, gold hoặc corpus theo test. Không đổi cấu hình thắng sau khi thấy baseline có Hit@1 tốt hơn. Tập test này nay đã được dùng để đánh giá; thay pipeline sau đó cần test mới nếu muốn tuyên bố holdout độc lập.

## Trace và kiểm chứng

Mỗi profile có records.json và summary.json; từng query có original_query.json, agent_trace.json, evaluation.json, embedding_usage.json, context_selection.json, context.txt và model_context.txt. Run manifest chứa freeze và hash; bản freeze không bị ghi đè.
