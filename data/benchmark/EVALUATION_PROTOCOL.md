# Quy tắc đánh giá DAY07 — phiên bản 1.0

Quy tắc được ghi trước benchmark DAY07. Phép thử dense một câu để kiểm tra kết nối DAY06 trước đó là smoke check, không dùng để chọn cấu hình. Đây là đặc tả cho runner sẽ triển khai; starter hiện tại chưa tự đọc JSON hoặc áp dụng đầy đủ quy tắc này.

Cấu hình máy đọc: [evaluation_protocol.json](evaluation_protocol.json). Benchmark: [questions.json](questions.json). Các SHA-256 trong JSON khóa corpus/chunk và bộ câu hỏi tại thời điểm chốt. Không chạy API hay đo điểm khi tạo tài liệu này.

## 1. Evidence hợp lệ và nguồn

- Chuẩn hóa Unicode NFC, gộp whitespace thành một dấu cách; giữ nguyên dấu câu, số, đơn vị và điều kiện. Exact match sau chuẩn hóa chỉ là bộ kiểm tra tự động ban đầu.
- Một evidence hợp lệ phải truy được source_id, trang PDF vật lý từ 1 và đoạn nguồn. Source/page phải đúng hoặc thuộc alternative đã xác minh.
- Nội dung cần hỗ trợ đầy đủ các ý bắt buộc trong expected_answer, gồm điều kiện, ngoại lệ, năm, đơn vị và thực thể được hỏi. Không lấy đáp án ngoài corpus.
- gold là danh sách evidence thay thế (OR), không phải danh sách mọi đoạn đều bắt buộc. Mỗi câu answerable hiện có ít nhất một gold nằm trọn trong một chunk.
- Không coi source/page đúng, similarity cao, citation ID hợp lệ hoặc verifier đồng ý là đủ để chứng minh trả lời đúng.

### Bằng chứng tương đương

Chấp nhận diễn đạt khác hoặc đoạn ngắn hơn gold nếu vẫn đủ mọi ý/điều kiện. Đối chiếu bản PDF và ghi quyết định riêng gồm query_id, chunk_id, source_id, page, quote, ý được hỗ trợ, nhãn và lý do. Áp dụng cùng quyết định cho mọi phương pháp có cùng query/chunk; không chấm ưu ái cấu hình được chọn.

Giữ cả điểm literal và điểm sau review. Không ghi đè gold, trace hoặc metric gốc. Nhãn hỗ trợ AI phải có provenance và xác nhận của học viên; không tự ghi confirmed khi chưa được xác nhận. Review không được dùng để sửa hệ thống sau khi xem test.

### Trường hợp cần nhiều chunk

Hit@1/Evidence Hit@3 chính: một chunk ở top-1/top-3 phải đủ evidence hoặc tương đương; không ghép chunk để biến thành hit.

Context Evidence Rate: được phép kết hợp nhiều chunk trong context cuối nếu đủ tập ý/điều kiện và nguồn. Vì vậy context đủ không bắt buộc kéo theo Hit@3.

Bộ 24 câu hiện tại không có câu được thiết kế bắt buộc multi-hop. Nếu chỉ có nhiều chunk ghép mới đủ cho một câu, ghi lỗi fragmented_evidence và chấm context riêng. Nếu sau này bổ sung câu multi-hop, tạo phiên bản benchmark mới trước test; khai báo nhóm evidence bắt buộc bằng AND, alternative trong từng nhóm bằng OR, báo Multi-evidence Coverage riêng. Không dùng metric một-chunk của baseline mẫu để đại diện điểm multi-hop.

## 2. Context budget và cách chọn context

Cấu hình gốc dùng 4.000 ký tự; cải thiện context dùng 6.000 ký tự. Đơn vị là số Unicode code point theo len(str) của toàn chuỗi evidence context cuối, gồm ID, source, page, nội dung và dấu phân cách, không phải token hay byte.

Block chuẩn:

~~~text
[chunk-id | source | page N]
text
~~~

Giữ nguyên text và nguồn. Không cắt giữa chunk để ép budget; chunk không vừa bị bỏ, tiếp tục xét candidate sau. Deduplicate theo ID. Cùng ID có nội dung khác là lỗi snapshot. Không dùng gold để chọn hay cắt context.

Mỗi lần search trả tối đa 10 kết quả đã xếp hạng; vẫn xuất top-3 để tính ranking. Dense: cosine exact search; lexical: TF-IDF; hybrid: mỗi nhánh lấy 10, hợp nhất RRF với k=60, dedup ID, trả 10 đầu. Với lexical/hybrid, phải áp dụng cùng metadata filter trên corpus đủ điều kiện trước xếp hạng; baseline mẫu hiện chưa làm việc này.

Trong một lượt tìm, thứ tự context theo rank retriever, hòa điểm theo chunk ID. Qua nhiều lượt, sắp candidate duy nhất theo reciprocal rank tốt nhất đạt được trong bất kỳ lượt nào, 1/(60+rank), hòa theo chunk ID; đóng gói lại từ toàn bộ candidate ở mỗi lượt. Lặp lại cùng chunk không cộng điểm. Không giữ cố định chunk lượt đầu nếu lượt sau có bằng chứng xếp cao hơn.

Giới hạn 2 lần retrieval và tối đa 3 quyết định model (search/search/answer) cho mọi cấu hình so sánh. Dừng khi trả lời đủ nguồn, từ chối vì thiếu evidence hoặc hết lượt. Không hard-code một ngưỡng cosine thành xác suất đủ bằng chứng.

Context budget chỉ giới hạn phần evidence gửi model; system prompt/câu hỏi/tokens đáp án được đo riêng. Cùng model, prompt, generation settings và giới hạn output giữa các cấu hình. Chọn và ghi model agent cụ thể trước lần benchmark đầu; JSON hiện để null vì chưa cấu hình model agent thật.

## 3. Filter và query

Chỉ sử dụng question cùng filter tường minh từ câu hỏi/ngữ cảnh người dùng. Các câu có filter trong benchmark: d7-dev-03, d7-dev-09, d7-test-01, d7-test-03. Cho phép section, language, year; bộ hiện tại chỉ dùng section.

Không lấy scope từ gold/page/đáp án. Không tự suy ra filter từ nhãn answerable hoặc absence_reason. Áp dụng filter cho cả dense, lexical, hybrid. Câu filter null tìm trên toàn bộ corpus; filter không có kết quả trả rỗng, không tự bỏ filter để lấy đáp án.

Xuất ranking của query gốc cho cả ba phương pháp, kể cả khi agent không gọi tool hoặc viết lại query. Ranking query viết lại/multi-hop và context pipeline báo riêng, không thay điểm query gốc. Agent có thể chọn query ở tối đa hai lượt; log query và kết quả từng lượt.

## 4. Metrics và mẫu số

| Chỉ số | Quy tắc |
|---|---|
| Hit@1 | Số câu có evidence đủ trong chunk top-1 / số câu có đáp án |
| Evidence Hit@3 | Số câu có ít nhất một chunk đủ evidence trong top-3 / số câu có đáp án |
| Context Evidence Rate | Số câu có context cuối đủ evidence và nguồn / số câu có đáp án |
| Context grade | 0: không evidence; 1: thiếu nội dung/điều kiện/nguồn; 2: đủ evidence và nguồn |
| Grounded answer | Câu có đáp án: 0 sai/thiếu căn cứ hoặc từ chối; 1 đúng một phần; 2 đúng đủ, được evidence hỗ trợ |
| Citation validity | Số citation trong context cuối và hỗ trợ khẳng định được gắn nguồn / tổng citation |
| Citation coverage | Số câu trả lời có citation / số câu trả lời; từ chối không tính là answered |
| Tool use | Số case có retrieval event / số case chạy thành công |
| Abstention đúng | Số câu thiếu evidence được từ chối, không suy đoán / số câu thiếu evidence |
| False abstention | Số câu có đáp án bị từ chối / số câu có đáp án |

Retrieval/context dùng mẫu số 15 dev hoặc 5 test cho câu có đáp án, không cộng 4 câu thiếu bằng chứng. Agent chạy toàn bộ 17 dev hoặc 7 test. Báo n/N và tỷ lệ; grounded/context grades báo số ở 0/1/2 và mean /2. Citation 0/0 ghi không áp dụng, không coi là 100%.

Lỗi retrieval làm ranking/context rỗng, tính miss trong metrics trên toàn bộ câu answerable; log stage/error và thời gian thật. Với agent, báo coverage và số lỗi riêng. starter/agent_metrics.py loại status=error khỏi quality denominators; nếu dùng script này phải ghi rõ mẫu số câu thành công, đồng thời báo metrics trên toàn bộ case (lỗi là không đạt) để không che mất lỗi. Lỗi không được tính là abstention đúng. Dùng tỷ lệ trên toàn bộ case cho quyết định chọn cấu hình.

Đọc và chấm cả 5 câu test answerable và 2 câu thiếu evidence cho baseline và cấu hình chọn. Kiểm tra từng citation với PDF, không chỉ ID. Không lấy expected_answer hay nhãn làm đầu vào model.

Thời gian: milliseconds cho query/tool, seconds cho tổng run, ghi phạm vi có/không gồm API/retry. Ghi token usage thực từ provider, model ID và USD từng run nếu có; không có giá trị thì null và giải thích, không tự ghi 0. Dùng chung embedding cache nếu có và báo rõ cache hit/miss cùng chi phí khởi tạo; không coi thời gian cache-hit là embedding lần đầu.

## 5. Các cấu hình sẽ thử trên dev

| ID | Phương pháp | Candidate trả về | Budget | Vai trò |
|---|---|---:|---:|---|
| dense_4000 | Dense DAY06 B | 10 | 4.000 ký tự | Baseline |
| lexical_4000 | TF-IDF | 10 | 4.000 ký tự | Phương pháp thứ hai |
| hybrid_4000 | Dense + TF-IDF, RRF k=60 | 10 | 4.000 ký tự | Phương pháp thứ ba; cải thiện 1 so với dense |
| hybrid_6000 | Cùng hybrid_4000 | 10 | 6.000 ký tự | Cải thiện 2: chỉ đổi context budget |

Cả bốn dùng cùng snapshot 162 chunk, benchmark, filter, agent model/prompt và giới hạn lượt. Không đổi top-k đơn thuần rồi gọi là phương pháp mới. Không yêu cầu cải thiện phải tăng điểm; báo kết quả không cải thiện và ít nhất hai lỗi dev kèm giả thuyết.

## 6. Chọn cấu hình và đóng băng trước test

Chọn theo thứ tự ưu tiên lexicographic trên dev (không cộng trọng số tùy ý):

1. Ít lỗi hệ thống hơn; báo tỷ lệ hoàn thành trên 17 case.
2. Grounded answer mean cao hơn trên toàn bộ 15 câu answerable (lỗi chấm 0).
3. Abstention đúng cao hơn trên cả 2 câu thiếu evidence (lỗi không đạt).
4. Citation validity cao hơn; 0 citation là không áp dụng và xếp sau tỷ lệ hợp lệ khi hòa các mục trước.
5. Context Evidence Rate cao hơn, rồi Evidence Hit@3, rồi Hit@1.
6. Nếu toàn bộ chất lượng hòa: ưu tiên USD thấp hơn khi mọi cấu hình có cost thật so sánh được; nếu thiếu cost, đánh dấu bỏ tiêu chí này và dùng latency end-to-end trung vị thấp hơn.
7. Nếu vẫn hòa: ưu tiên budget nhỏ hơn, rồi ID cấu hình theo alphabet.

Raw-query ranking và agent pipeline có thể khác nhau; lưu cả hai để giải thích. Không dùng test hoặc chi phí/điểm DAY06 để đổi thứ tự ưu tiên này.

Trước test tạo bản ghi freeze gồm protocol hash, hash benchmark/chunks, model và generation settings, prompt hash, cấu hình thắng và metric dev. JSON trong task này chỉ khóa quy tắc và đầu vào; selected_configuration=null là có chủ ý vì chưa chạy dev, không được điền giả. Model agent và prompt hash cũng phải được điền ở run manifest trước benchmark đầu tiên, giữ cố định khi so sánh. Muốn thay quy tắc sau khi đã chạy dev thì ghi phiên bản/lý do và chạy lại toàn bộ dev; sau test không được tune trên tập đó rồi báo holdout độc lập.

## 7. Tách gold khỏi runtime

Loader benchmark chỉ ở phía evaluator. Runner tạo input bằng allowlist question/filter; query_id dùng để ghi log, không gửi như gợi ý đáp án. Controller/retriever không được nhận expected_answer, gold, answerable, expected_behavior, origin, absence_reason, absence_verification, matching_chunk_ids hoặc evidence checks.

cases.json là dữ liệu tổng hợp nhãn, không phải payload agent. Không đưa nguyên file benchmark/validation vào prompt. Prompt yêu cầu chỉ dựa vào evidence, coi tài liệu là dữ liệu thay vì chỉ dẫn, trả lời có citation hoặc nói không đủ thông tin. Test logger không được đưa gold vào history/tool messages.

Kiểm tra trước run: hash đầu vào khớp protocol, chunk IDs độc nhất, filter đúng allowlist, payload model/tool không có trường gold, context trong budget. Test mock kiểm tra code không thay benchmark thật; không tự chạy smoke test API khi import test suite.

## 8. Phạm vi task hiện tại

Đã chốt quy tắc và kế hoạch cấu hình; chưa triển khai runner, lexical filter, RRF, controller thật, context nhiều lượt theo quy tắc này hoặc chạy benchmark. Bước tiếp theo là triển khai ba retriever và runner tuân thủ protocol, sau đó đo dev.
