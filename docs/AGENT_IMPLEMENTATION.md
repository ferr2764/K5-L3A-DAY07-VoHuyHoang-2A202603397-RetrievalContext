# Agent thật DAY07 — task 5

## Controller và retriever

OpenRouterController.decide(question, history) dùng OpenAI-compatible chat completions và native function calling trên OpenRouter. Ba tool: search(query), finish(answer, citations), abstain(reason). Model mặc định openai/gpt-4.1-mini; có thể đặt AGENT_MODEL trong starter/.env hoặc dùng --model. Không đổi model giữa cấu hình so sánh; model/prompt/tools hash và generation settings được ghi trước khi gọi model.

Retriever.search dùng ba triển khai task 4: dense pgvector DAY06 B, lexical TF-IDF và hybrid RRF. Profile lấy từ data/benchmark/evaluation_protocol.json. CLI nhận question/filter tường minh, không đọc nhãn/gold vào controller. Hash benchmark được kiểm tra bằng bytes, không đưa nội dung benchmark vào model.

Agent giới hạn 2 retrieval và 3 model decisions; top-k 10; context 4.000 hoặc 6.000 ký tự theo profile. Dedup ID, repack candidate theo best reciprocal rank qua các lượt, giữ source/page, không cắt chunk. Lịch sử gửi model chỉ chứa câu hỏi, system prompt và cặp assistant/tool của lượt search gần nhất với context tích lũy đã giới hạn budget.

## Chạy từ gốc DAY07

Dùng virtual environment đã cài starter/requirements.txt. Database DAY06 cần đang chạy; starter/.env cần DATABASE_URL, OPENROUTER_API_KEY, EMBEDDING_MODEL đúng. Không ghi API key vào lệnh hoặc commit file .env.

~~~powershell
python -X utf8 scripts/run_agent.py --profile dense_4000 --question "Agile chia dự án thành những đơn vị nào?" --section 1.2
python -X utf8 scripts/run_agent.py --profile hybrid_4000 --question "Câu hỏi của bạn"
~~~

--profile nhận dense_4000, lexical_4000, hybrid_4000, hybrid_6000. --model chọn model khác một cách tường minh; mặc định openai/gpt-4.1-mini. --output nhận thư mục run mới, không cho ghi đè thư mục hiện có. --section, --language, --year là filter người dùng cung cấp.

Đây là chạy agent thật, có phí model và embedding khi cache miss. Không lấy chi phí DAY06 $0.0018 làm chi phí DAY07. Usage/token và cost do provider trả được giữ theo mỗi model call; phần embedding chưa được adapter ghi lại thì để null, không tự ghi 0. Các lần smoke thử lỗi/rejection cũng có thể phát sinh phí.

## Trace và lỗi

Mỗi run nằm ở artifacts/agent_runs/<UTC timestamp>/:

- run_manifest.json: model, generation settings, prompt/tool hash, profile, protocol hash, hash đầu vào.
- trace.json: status answered/abstain/error; câu hỏi/filter, tool call/query/results, context cuối/IDs, câu trả lời/citation, model request/response/usage, số lượt và thời gian.
- cli_error.json nếu xảy ra lỗi sau khi đã lưu trace, tránh ghi đè kết quả.

Lỗi provider/database/schema/timeout ghi status=error và stage/type/http status, không thay bằng abstention hoặc mock. Nội dung lỗi provider có thể chứa thông tin nhạy cảm nên không lưu nguyên error body. UTF-8 được bật khi in tiếng Việt trên Windows.

Citation phải có trong context cuối. Nếu model liệt kê ID hợp lệ trong citations nhưng quên marker trong answer, renderer thêm đúng các ID model đã cung cấp ở cuối đoạn; trace lưu raw_model_answer và citation_rendering. Không tạo ID mới, không sửa ID ngoài context. ID không hợp lệ hoặc answer không có citation hợp lệ dẫn tới abstain với stop_reason riêng. Có ID đúng chỉ chứng minh truy vết; vẫn cần chấm nội dung nguồn hỗ trợ từng khẳng định ở bước đánh giá.

## Kiểm tra offline

~~~powershell
python -B -m unittest discover -s tests -p test_agent_runtime.py -v
~~~

Chỉ chọn test mới: tests/test_dense.py của người dùng hiện gọi API khi import nên không chạy toàn bộ discovery một cách vô ý. Các test offline dùng fixture để kiểm tra contract, không được báo làm benchmark chất lượng model.

Đã kiểm tra real model với câu Agile đã dùng ở smoke task 4, không phải tập test DAY07. Các lần đầu gặp lỗi console/citation formatting được giữ trong trace riêng; lần thành công có search thật và answer có nguồn. Đây là integration check, chưa phải chạy dev, chọn cấu hình hoặc đánh giá test. Nếu thay prompt sau smoke, manifest hash của lần tiếp theo phản ánh thay đổi; chỉ bắt đầu benchmark sau khi chốt model/prompt.

Nguồn API: [OpenRouter tool calling](https://openrouter.ai/blog/tutorials/tool-calling/), [model mặc định](https://openrouter.ai/openai/gpt-4.1-mini).
