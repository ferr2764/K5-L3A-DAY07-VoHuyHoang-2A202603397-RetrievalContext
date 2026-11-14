# Báo cáo DAY07 — Retrieval & Context Engineering

**Học viên:** Võ Huy Hoàng · **MSSV:** 2A202603397 · **Lớp:** L3A
**Repo:** https://github.com/ferr2764/K5-L3A-DAY07-VoHuyHoang-2A202603397-RetrievalContext
**Ngày hoàn thiện:** 14/11/2026. Phạm vi: bài cơ bản; chưa thực hiện thử thách nâng cao.

## 1. Dữ liệu, quyền sử dụng và benchmark

Nguồn: *Foundations of Information Systems*, Mahesh S. Raisinghani, OpenStax/Rice University, 2025. Access for free at openstax.org. Text được chia sẻ cho bài tập phi thương mại theo **CC BY-NC-SA 4.0**, giữ attribution; nội dung bên thứ ba có thể có quyền riêng. Xem [manifest nguồn](../../data/day6/source_manifest.json), [attribution](../../data/day6/ATTRIBUTION.md) và [snapshot](../../data/day6/snapshot.json).

Phạm vi trang PDF vật lý 30–72, đánh số từ 1: 43 trang được chọn, 34 trang nội dung được index sau khi loại 43–51. Trang in = trang PDF − 10 trong phạm vi này. Chuẩn hóa Unicode NFC/khoảng trắng; không OCR. Dùng nguyên **162 chunk strategy B của DAY06**, chia theo đoạn, tối đa 1.000 ký tự, không overlap; không chia lại giữa các phương pháp. Đoạn nối trang, header/footer và caption còn có thể gây nhiễu. Snapshot có SHA-256 trong protocol; bản có thể đưa lên Git ở data/day6/chunks.json, không chứa vector/PDF nguyên cuốn.

Vector store thật: PostgreSQL **16.16**, pgvector **0.8.7**, bảng day6_chunks, strategy B, exact cosine. Embedding document/query: OpenRouter **openai/text-embedding-3-small**, **1.536 chiều**. Agent: OpenRouter **openai/gpt-4.1-mini**, temperature 0, max_tokens 800, timeout 60 giây, SDK retries 2. SDK DAY07: openai 3.51.0, psycopg 3.3.9, python-dotenv 1.2.4; phân tích PDF dùng pypdf 6.21.4. Không có revision nội bộ model để bảo đảm tái lập bit-for-bit.

[Benchmark](../../data/benchmark/questions.json) có **24 câu: dev 17 = 15 có evidence + 2 thiếu; test 7 = 5 có evidence + 2 thiếu**. Có câu trực tiếp, diễn đạt lại, điều kiện/ngoại lệ; filter được cung cấp trước truy xuất, gồm dev-03/dev-09/test-01/test-03. Chủ đề dev chủ yếu mục 1.3–2.1; test có đáp án thuộc mục 2.2. Đáp án, trang, gold evidence và kiểm chứng chuẩn hóa nằm trong [validation](../../data/benchmark/validation.json). Các đoạn gold có đáp án được đối chiếu PDF và chunk hiện hữu; không dùng câu thiếu đáp án cho retrieval metrics.

Nguy cơ rò rỉ: 15 câu dev kế thừa DAY06 nên đã quen dữ liệu; test tách chủ đề nhưng cùng sách, có thể cùng chunk chứa ngữ cảnh lân cận. Một trợ lý hỗ trợ cả benchmark, code và review nên có thiên lệch, không phải đánh giá mù. Model/retriever chỉ nhận câu hỏi và filter đã cung cấp, không nhận đáp án, gold, split hoặc nhãn answerable. Không thay bộ test sau khi xem kết quả.

## 2. Quy tắc đánh giá và cấu hình

[Protocol trước thử nghiệm](../../data/benchmark/EVALUATION_PROTOCOL.md) và [JSON](../../data/benchmark/evaluation_protocol.json) cố định dữ liệu, nhãn và cách tính. Evidence hợp lệ phải hỗ trợ ý cần trả lời, đúng nguồn/trang sau chuẩn hóa; hỗ trợ tương đương được xét theo nội dung, không chỉ ID. Nếu có nhiều nguồn hợp lệ thì chấp nhận bất kỳ nguồn hợp lệ nào. Với câu cần nhiều chunk phải có đủ các ý; 20 câu có đáp án hiện tại đều có gold trong một chunk, chưa kiểm tra multi-hop.

Hit@1 và Evidence Hit@3 đo ranking của **câu hỏi gốc**; Context Evidence Rate (CER) đo evidence trong **context cuối thực gửi model**, có thể từ query model viết lại và nằm ngoài top-3. Mẫu số chỉ gồm 15 câu dev hoặc 5 câu test có đáp án. Chỉ số tự động dưới đây kiểm tra literal evidence đã chuẩn hóa; đánh giá hỗ trợ ngữ nghĩa được lưu riêng.

Cả bốn cấu hình lấy 10 candidate, không reranker; hybrid kết hợp dense và TF-IDF bằng RRF với k=60, mỗi nhánh 10 candidate. Filter metadata áp dụng trước xếp hạng, không suy từ gold. Context dedup theo ID, xếp theo độ liên quan, giữ nguyên chunk đầy đủ cùng nguồn/trang/metadata; block không vừa thì bỏ, không cắt mất điều kiện. Budget **4.000 hoặc 6.000 ký tự Python len**, tính cả header và separator, không phải token. Mọi quyết định chọn/bỏ chunk và context thực gửi model đều có trace.

Controller gọi model thật quyết định search/finish/abstain qua function tools; bắt buộc tìm trước trả lời, tối đa 2 search và 3 lượt quyết định. Citation phải thuộc context. Lỗi provider/schema được ghi thật, không dùng mock. Guard có thể chuyển câu có citation không hợp lệ thành từ chối; đây khác lỗi HTTP và được đánh giá false abstention nếu nguồn thực sự có đáp án.

## 3. So sánh retrieval và thời gian/chi phí

| Cấu hình | Phương pháp; budget ký tự | Split | Hit@1 | Evidence Hit@3 | CER | Median truy xuất gốc (ms) | Median agent (s) | Chi phí hiệu lực (USD) |
|---|---|---|---|---|---|---|---|---|
| dense_4000 baseline | Dense; 4.000 | dev | 8/15 (53,3%) | 13/15 (86,7%) | 13/15 (86,7%) | 900,70 | 4,66 | 0,01967950 |
| lexical_4000 | TF-IDF; 4.000 | dev | 7/15 (46,7%) | 11/15 (73,3%) | 11/15 (73,3%) | 0,36 | 3,99 | 0,01772680 |
| hybrid_4000 cải thiện 1 | RRF; 4.000 | dev | 8/15 (53,3%) | 12/15 (80,0%) | 12/15 (80,0%) | 869,04 | 4,74 | 0,02028616 |
| hybrid_6000 cải thiện 2 / chọn | RRF; 6.000 | dev | 8/15 (53,3%) | 12/15 (80,0%) | 14/15 (93,3%) | 889,79 | 4,80 | 0,02417208 |
| dense_4000 baseline | Dense; 4.000 | test | 3/5 (60,0%) | 4/5 (80,0%) | 5/5 (100%) | 892,14 | 4,41 | 0,00808006 |
| hybrid_6000 đã chốt | RRF; 6.000 | test | 1/5 (20,0%) | 4/5 (80,0%) | 5/5 (100%) | 882,30 | 4,53 | 0,00930324 |

Latency đo trong môi trường local/network của lượt chạy, profile chạy đồng thời nên không coi đây là benchmark tải chuẩn. Thời gian agent và truy xuất gốc là hai phép đo riêng, không cộng các median để suy tổng thời gian.

Lượt dev đầu có **19 lỗi/68 case**: 18 HTTP 402 và 1 InvalidToolSchema. Sau khi học viên bổ sung credit/limit, chỉ chạy bù đúng 19 case lỗi, giữ 49 case thành công, không chọn đáp án đẹp nhất. Kết quả hiệu lực đủ 68 case, không còn lỗi provider; toàn bộ attempt gốc vẫn được lưu. [Kết quả dev](../../artifacts/dev_retries/20261114T093849461754Z/summary.json) và [lịch sử lỗi](../../artifacts/dev_benchmark/20261114T092856910861Z/summary.json).

Chi phí hiệu lực trong bảng gồm chat và embedding cho mỗi profile; không gồm attempt bị thay thế. **Dev mọi attempt có usage biết được: $0.08380398; test: $0.01738330; cộng benchmark biết được: $0.10118728.** Đây không phải tổng hóa đơn tài khoản: chưa gồm smoke/demo trước đó và 18 request lỗi không trả usage vẫn là unknown, không mặc định miễn phí. TF-IDF không tốn embedding nhưng agent vẫn tốn chat.

## 4. Hai cải thiện và phân tích lỗi dev

Cải thiện 1 đồng thời là phương pháp mới: dense → hybrid RRF, kỳ vọng lexical bổ sung exact-term. Thực tế Hit@3/CER giảm 13/15 → 12/15 ở budget 4.000; không mặc định hybrid luôn tốt hơn. Cải thiện 2 giữ nguyên hybrid/candidate/ranking, tăng budget 4.000 → 6.000; CER tăng 12/15 → 14/15. [Phân tích và bằng chứng](../../docs/DEV_IMPROVEMENTS.md), [nhãn từng lỗi](../../artifacts/dev_improvements/analysis.json).

| Lỗi dev | Nguyên nhân và giả thuyết | Trước → sau trên cùng candidate |
|---|---|---|
| d7-dev-05, SFIA, PDF 32 | Gold Level 5 ở rank 6; block 1.046 ký tự nhưng budget 4.000 chỉ còn 160. Giả thuyết: budget lớn giữ được đoạn phân biệt Level 5/6. | hybrid_4000 bỏ gold, trả nhầm Level 6 → hybrid_6000 còn 1.410 ký tự, giữ gold và trả đúng Level 5. |
| d7-dev-11, Velocity, PDF 56 | Gold rank 6, block 932 ký tự, chỉ còn 191 nên bị bỏ. Model nêu Velocity nhưng dẫn chunk Volume/Variety. | hybrid_4000 citation không hỗ trợ → hybrid_6000 còn 1.231 ký tự, giữ gold và citation đúng. |
| d7-dev-04, SFIA, PDF 32 | RRF đẩy evidence xuống thấp; sau query viết lại gold rank 8, budget 6.000 chỉ còn 439 < 1.046. | Vẫn thiếu gold và trả nhầm Level 5 thay Level 3; cải thiện budget không sửa mọi lỗi. |

Chọn theo thứ tự protocol: ít lỗi, grounded mean cao hơn, abstention/citation/CER/retrieval rồi chi phí/latency/budget khi hòa. Grounded dev mean lần lượt dense 1,33; lexical 1,33; hybrid_4000 1,47; hybrid_6000 **1,60/2**. Vì vậy chọn **hybrid_6000**, baseline dense_4000. Nhãn dev do AI hỗ trợ, đã được học viên xác nhận.

[Freeze](../../artifacts/selection/20261114T095320637430Z/freeze.json) tạo lúc **09:53:20 UTC**, trước test bắt đầu **09:53:37 UTC** ngày 14/11/2026, chứa hash code/prompt/protocol/dữ liệu và lựa chọn. Test chạy cùng 7 câu cho baseline và cấu hình chọn, đủ 14 trace, không lỗi provider; không chỉnh pipeline hoặc lựa chọn theo test.

## 5. Đánh giá agent, context và citation trên test

| Cấu hình | Tool use | Search/case | Context 0/1/2; mean | Grounded 0/1/2; mean | Citation hỗ trợ đủ | Answer có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|---|
| dense_4000 | 7/7 | 1 | 0/0/5; 2,00 | 0/2/3; 1,60/2 | 4/6 (66,7%) | 5/5 | 2/2 | 0/5 |
| hybrid_6000 | 7/7 | 1 | 0/0/5; 2,00 | 1/2/2; 1,20/2 | 2/4 (50,0%) | 4/4 | 2/2 | 1/5 |

Grounded/context dùng 5 câu có đáp án; abstention dùng 2 câu thiếu evidence; tool use dùng cả 7. Mỗi case thành công có 2 lượt model. Citation hỗ trợ một phần không được tính là hỗ trợ đầy đủ toàn bộ claim; giữ rõ cả phần đúng và phần suy diễn trong nhãn. Không có citation là N/A theo case, không coi là 100%.

Đã đọc 14 đáp án xuất bản, 10 context cho câu có đáp án và 10 citation xuất bản, đối chiếu PDF. [Nhãn/nguồn đánh giá](../../artifacts/test_review/20261114T095337524594Z/summary.json), [giải thích từng câu](../../docs/TEST_REVIEW.md). **Review do Codex hỗ trợ, human_confirmation/student_confirmation = confirmed theo xác nhận của học viên**; đây vẫn không phải chấm mù độc lập.

Test-03 hybrid có đủ context nhưng citation nhóm [id1, id2] bị guard từ chối, nên chấm đáp án xuất bản là 0 và false abstention. Test-04 cả hai nêu đúng Different objectives nhưng thêm quan hệ nhân quả giữa hai nguyên nhân riêng trong sách; test-05 thêm suy luận hậu quả ngoài đoạn dẫn. Hai câu này chấm 1/2 dù ý chính đúng. Giữ nguyên lỗi sau test.

## 6. Demo ba tình huống từ trace thật

Chạy từ root DAY07, không cần API/database:

~~~powershell
python scripts/demo_saved_traces.py --case all
~~~

Đây là **phát lại kết quả đã chạy thật**, không phải lần gọi model mới. Script kiểm tra hash trace, in câu hỏi/đáp án/nguồn-trang hoặc lỗi. [Manifest demo](../../artifacts/demo/demo_cases.json).

| Tình huống | Query / trace | Kết quả đã lưu |
|---|---|---|
| Trả lời có nguồn | hybrid_6000 / d7-test-01 | Ba cách IT tạo giá trị: automation, information generation, transformation/routines; citation 66402ed6…638da, Foundations of Information Systems, PDF 62. Grounded 2/2. |
| Từ chối đúng | hybrid_6000 / d7-test-06 | Hỏi giá thuê bao Cohealo + Clinical/tháng năm 2025; trả “Không đủ bằng chứng trong tài liệu để trả lời.” Corpus có mô tả sản phẩm nhưng không có giá. |
| Lỗi thật | dev lần đầu / dense_4000 / d7-dev-12 | APIStatusError, HTTP 402 ở model; không xuất đáp án, không fallback. Trace gốc được giữ dù đã chạy bù thành công. |

## 7. Hướng dẫn chạy từ root DAY07

### Môi trường và xem lại bài nộp offline

Windows PowerShell, Python có venv; dependency được ghim theo lượt chạy. Không dùng unittest discover toàn thư mục vì tests/test_dense.py là smoke gọi API thật ngay khi import.

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements-submission.txt
python scripts/restore_submission_data.py
python -B -m unittest tests.test_agent_runtime tests.test_context_builder tests.test_retrieval_methods tests.test_dev_evaluation -v
python scripts/demo_saved_traces.py --case all
~~~

Restore kiểm tra SHA-256 rồi chép data/day6/chunks.json sang starter/data/day6/chunks.json, đúng đường dẫn frozen; từ chối ghi đè nếu dữ liệu hiện tại khác. Xem JSON/CSV/Markdown trong artifacts để review kết quả mà không gọi API.

### Kết nối lại DAY06 và OpenRouter để chạy thật

Cần index DAY06 đã ingest **strategy B 162 chunk, vector 1.536 chiều**. Bản nộp không chứa dump PostgreSQL/vector; snapshot text không tự tạo vector index. Dùng DB DAY06 hiện có. Nếu máy mới chưa có DB, dựng DAY06 theo [báo cáo DAY06](https://github.com/ferr2764/K5-L3A-DAY06-VoHuyHoang-2A202603397-DataIngestion/blob/main/report/individual/2A202603397_VoHuyHoang.md): tải PDF từ publisher, kiểm hash manifest, chạy pipeline embedding thật. Các bước đó cần mạng/credit; không thể thay bằng DB rỗng.

Nếu đã có workspace DAY06 và volume cũ, khởi động từ thư mục starter của DAY06:

~~~powershell
docker compose -p day6_student_starter up -d --wait
~~~

Quay về root DAY07. Tạo file local starter/.env (không commit):

~~~dotenv
DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
OPENROUTER_API_KEY=your_openrouter_key
EMBEDDING_MODEL=openai/text-embedding-3-small
AGENT_MODEL=openai/gpt-4.1-mini
~~~

Dùng URI thật nếu DB khác; model/dimension/index phải khớp. Dense adapter kiểm snapshot so với DB, không âm thầm dùng dữ liệu khác.

~~~powershell
python scripts/run_agent.py --profile hybrid_6000 --question "Agile chia dự án thành những đơn vị nào?"
python scripts/run_agent.py --profile hybrid_6000 --question "Theo corpus này, giá thuê bao Cohealo + Clinical mỗi tháng năm 2025 là bao nhiêu USD?"
~~~

Mỗi lần gọi thật tốn phí, tạo thư mục mới artifacts/agent_runs với trace.json, context.txt, model_context.txt, context_selection.json và manifest. Lỗi API cũng được lưu, không fallback. Có thể dùng --section/--language/--year khi câu hỏi/ngữ cảnh đã cung cấp filter trước retrieval.

### Lệnh thí nghiệm (tham khảo, không cần chạy lại để xem bài)

~~~powershell
python scripts/run_dev_benchmark.py
python scripts/analyze_dev_improvements.py
python scripts/select_dev_configuration.py
python scripts/run_test_benchmark.py --freeze artifacts/selection/20261114T095320637430Z/freeze.json
~~~

Dev runner ghi run mới; chỉ dùng retry_dev_errors.py cho case lỗi và đúng run được chỉ định (xem --help). Script phân tích/review PDF cần bản PDF DAY06 ở đường dẫn sibling như manifest; dữ liệu/nhãn đã xuất không cần PDF để xem. Các lệnh phân tích/chọn mặc định tham chiếu lượt chạy đã lưu; không tự coi chúng là bộ điều phối chọn một lượt mới. Không chạy lại test để tối ưu hoặc thay test hiện tại. Lượt nộp sử dụng freeze và artifact có timestamp nêu trên.

## 8. Cấu trúc bài nộp, .gitignore và kiểm tra

Giữ nguyên README/SUBMISSION và các file đề bài gốc. [RUN_SUBMISSION.md](../../RUN_SUBMISSION.md) là điểm vào bổ sung; hướng dẫn đầy đủ nằm trong báo cáo này.

~~~text
data/benchmark/       câu hỏi, split, gold, validation và protocol
data/day6/            snapshot text được chia sẻ, checksum, manifest, attribution
src/                  retrieval, controller/agent và context builder
scripts/              chạy thật, phân tích, restore và demo offline
tests/                test offline và smoke dense riêng
docs/                 thiết kế và phân tích chi tiết
artifacts/            trace, context thực gửi model, usage, lỗi, freeze, nhãn và demo
report/individual/    báo cáo cá nhân này
starter/data/         runtime local được restore; vẫn bị ignore
starter/results/      output starter local; vẫn bị ignore
~~~

.gitignore đang ignore starter/data/ và starter/results/. Không bỏ ignore hoặc đưa .env lên Git. Chủ động đóng gói **data/day6/chunks.json** byte-identical và **artifacts/** ngoài đường dẫn ignore; benchmark ở data/benchmark/. Vector DB và PDF gốc không đóng gói; cách dựng lại/tiếp cận nêu ở trên. Xem [checklist bài nộp](../../docs/SUBMISSION_CHECKLIST.md).

## 9. Kết luận và giới hạn

Trên dev, tăng context giúp hybrid giữ evidence ở rank thấp và sửa được hai lỗi đã phân tích. Trên test, CER của cả hai đạt 5/5 nhưng grounded answer của baseline **1,60/2**, cao hơn hybrid **1,20/2**: retrieval đủ chưa bảo đảm câu trả lời đúng và citation parser còn gây từ chối nhầm. Giữ hybrid_6000 là cấu hình đã chọn trước test; không đổi sang baseline sau khi xem test.

Chỉ có một sách, 5 câu test có đáp án, một lượt model/config; không có CI hay kiểm định thống kê. Chưa kiểm tra multi-hop, OCR/bảng/ảnh, tải đồng thời chuẩn hoặc thử thách nâng cao 100 trang. Budget ký tự không bảo đảm token budget. Latency phụ thuộc mạng/provider; cost có phần unknown. Nhãn ngữ nghĩa do AI hỗ trợ đã được học viên xác nhận; không dùng việc citation tồn tại để suy đáp án có căn cứ.

Báo cáo và artifact đã chuẩn bị local; học viên đã xác nhận nhãn. Còn commit/push, kiểm quyền truy cập repo của người chấm và nộp link theo hướng dẫn giảng viên.

Xác nhận review hiện tại: [confirmation.json](../../artifacts/review_confirmation/confirmation.json); [bản nhãn dev đã xác nhận](../../artifacts/review_confirmation/dev_reviews_confirmed.json). Các trạng thái chờ xác nhận trong artifact lịch sử phản ánh thời điểm trước xác nhận, không phải việc còn thiếu ở bài nộp hiện tại.
