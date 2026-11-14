# Checklist bài nộp DAY07

Đối chiếu SUBMISSION.md, không sửa checklist gốc của đề bài.

- [x] Code dense pgvector DAY06, lexical TF-IDF, hybrid RRF; controller dùng model thật, không fallback mock.
- [x] Nguồn, model/dimension/vector store, license, snapshot text chia sẻ và hướng dẫn kết nối/tái tạo qua DAY06.
- [x] Benchmark 20 câu có evidence + 4 thiếu evidence, dev/test cố định, filter có trước retrieval.
- [x] Bốn cấu hình dev, hai cải thiện, ít nhất hai lỗi dev với nguyên nhân/giả thuyết/trước-sau.
- [x] Chọn cấu hình và freeze trước test; test baseline và cấu hình chọn, giữ đầy đủ lỗi/trace.
- [x] Nhãn hỗ trợ AI, lý do từng câu, bảng kết quả và giới hạn; human_confirmation/student_confirmation = confirmed theo xác nhận của học viên.
- [x] Báo cáo cá nhân điền đầy đủ; demo answer/citation, abstention và lỗi thật qua replay kiểm hash.
- [x] Không sửa .gitignore gốc; chuyển snapshot được phép chia sẻ sang data/day6/, kết quả ở artifacts/.
- [x] Học viên đã xác nhận nhãn dev/test trong phiên làm việc; trạng thái confirmed được ghi riêng, không sửa lịch sử freeze.
- [ ] Commit/push code, benchmark, data/day6, artifact, docs và báo cáo lên repo cá nhân.
- [ ] Kiểm quyền truy cập repo/link đã push và nộp link theo giảng viên.

Không làm thử thách nâng cao. Không đưa .env, API key, token, .venv hoặc vector DB có dữ liệu ngoài phạm vi chia sẻ lên repo. Không cần chạy lại test để hoàn tất bài nộp.

Ví dụ lệnh Git từ root DAY07, xem danh sách trước khi commit:

~~~powershell
git status --short
git check-ignore starter/data/day6/chunks.json
git add RUN_SUBMISSION.md report/individual/2A202603397_VoHuyHoang.md data/benchmark data/day6 src scripts tests docs artifacts starter/dense_retriever.py starter/requirements.txt
git diff --cached --stat
git diff --cached --check
~~~

Đây là hướng dẫn cho học viên; agent chưa commit hoặc push. Kiểm nội dung staged trước khi tự commit/push, đặc biệt không thêm credential. Bản snapshot đóng gói thay cho force-add dữ liệu trong starter/data.

Xem [rà soát file và thao tác còn lại](FINAL_FILE_REVIEW.md) và [xác nhận review](../artifacts/review_confirmation/confirmation.json).
