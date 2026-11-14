# Rà soát file và thao tác còn lại

## Đã xác nhận

Nhãn review dev/test và phân tích lỗi dev: **confirmed** theo yêu cầu của Võ Huy Hoàng trong phiên làm việc ngày 14/11/2026. Không đổi đáp án, điểm số, cấu hình chọn hoặc kết quả test.

- [Bản ghi xác nhận](../artifacts/review_confirmation/confirmation.json).
- [Nhãn dev đã xác nhận](../artifacts/review_confirmation/dev_reviews_confirmed.json).
- Nhãn test hiện tại trong artifacts/test_review/ và phân tích dev trong artifacts/dev_improvements/ đã cập nhật confirmed.
- [Danh mục file đã rà soát](../artifacts/review_confirmation/file_inventory.json): đọc các file văn bản, kiểm kê file khác; không sao chép nội dung credential hoặc đọc binary như văn bản.

## File còn cần thao tác của học viên

| File/vị trí | Thao tác | Khi nào |
|---|---|---|
| starter/.env | Điền key OpenRouter và DATABASE_URL của máy chạy; không commit | Khi chạy thật trên máy khác; môi trường hiện tại đã chạy được |
| data/day6/source_manifest.json và PDF ở workspace DAY06 | Tải đúng PDF/checksum và dựng index theo báo cáo DAY06 nếu chưa có DB | Chỉ khi tái tạo từ máy mới |
| Các file bài làm trong Git | Commit/push và kiểm quyền truy cập người chấm | Trước khi nộp |
| Link repo cá nhân | Nộp theo hướng dẫn giảng viên | Bước nộp bài |

Không còn mục bắt buộc phải điền tay trong báo cáo cá nhân. Không có xác nhận nhãn nào còn chờ ở trạng thái hiện tại.

## Ghi chú cũ đã xử lý

Đã cập nhật các câu chờ học viên xác nhận trong báo cáo, checklist và tài liệu phân tích. Ghi chú “chưa chọn cấu hình” trong tài liệu phân tích dev được thay bằng thông tin cấu hình đã chốt. Không tìm thấy TODO/FIXME trong code bài làm cần hoàn thành.

Không xóa nguyên file vì không có file nào được xác định chỉ là ghi chú sinh bài và không còn tác dụng: docs giải thích phương pháp, scripts phục vụ tái lập, artifacts giữ bằng chứng. Các mẫu MSSV_HoTen/README/SUBMISSION gốc thuộc đề bài được giữ nguyên theo yêu cầu trước đó; không cần điền thêm mẫu báo cáo khi báo cáo cá nhân đã hoàn chỉnh.

## Vì sao còn chữ pending ở một số file

- artifacts/selection/.../freeze.json, dev_reviews.json và dev_selection.json là bằng chứng trước test có checksum. Giữ nguyên, dùng bản xác nhận bổ sung để cập nhật trạng thái hiện tại.
- Trace, records, evaluation và summary của run gốc ghi trạng thái tại lúc chạy, trước bước review. Giữ nguyên dữ liệu thí nghiệm; bản review hiện tại và confirmation.json là nơi đọc trạng thái cuối.
- Code runner/review khởi tạo pending cho **lượt chạy mới** là đúng: xác nhận hôm nay không tự xác nhận output tương lai.
- Không thay pending bằng confirmed hàng loạt trong source vì có thể tuyên bố đã chấm cả những lượt chưa chạy/chưa review.

AI hỗ trợ tạo nhãn; học viên xác nhận không có nghĩa đây là chấm mù hoặc người review độc lập.
