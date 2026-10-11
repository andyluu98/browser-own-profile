# 01. Cơ chế hoạt động

## Ba cách để máy "nhìn" một trang web

| Cách | Máy nhận gì | Ưu | Nhược |
|---|---|---|---|
| Chụp màn hình | Một tấm ảnh, AI đoán nút nằm ở tọa độ nào | Dùng được với mọi thứ, kể cả phần mềm không phải web | Mỗi bước gửi ảnh nên tốn token, chậm, có thể bấm lệch |
| **Đọc cấu trúc trang** (bộ này dùng) | Danh sách chữ ngắn: `e3 nút "Đăng"` | Rẻ, nhanh, bấm đúng phần tử | Không thấy nút chỉ có hình mà không có tên |
| Kết hợp | Đọc cấu trúc, bí thì chụp ảnh | Linh hoạt | Phức tạp hơn |

Hãy hình dung trang web như một ngôi nhà. Chụp ảnh là đứng ngoài nhìn vào. Đọc cấu trúc là cầm bản vẽ: biết chính xác cửa nào ở đâu, cửa nào đang khóa.

## Bộ này làm từng bước ra sao

1. **Kết nối.** Chrome có một cửa dành cho chương trình bên ngoài, gọi là remote debugging (giao thức CDP). browser-harness mở kết nối qua cửa này. Playwright, Puppeteer, jev-ultrafast cũng đi đúng cửa này.
2. **Đọc trang.** `browser_kit/snapshot.js` chạy trong trang, gắn mã `e1`, `e2`... cho các nút và ô nhập, trả về danh sách gọn (tối đa 150 phần tử, 4.000 ký tự chữ). Mật khẩu, số thẻ, mã OTP bị xóa khỏi danh sách trước khi trả về.
3. **Chọn.** Code (hoặc AI) chỉ được chọn một mã trong danh sách, không được tự viết lệnh JavaScript chạy trong trang.
4. **Bấm.** Công cụ cuộn tới phần tử, kiểm tra nó không bị khóa, không bị che, rồi bấm vào giữa như người dùng bấm chuột.
5. **Chốt an toàn.** Ngay trước khi bấm, công cụ đọc lại tên nút. Trang vừa đổi "Tiếp" thành "Đăng" thì nó từ chối bấm.

## Vì sao chạy trong một tiến trình riêng

Phần nói chuyện với Chrome (`worker.py`) chạy tách khỏi chương trình chính. Chrome treo hay đóng ngang thì chỉ tiến trình đó chết, chương trình chính khởi động lại nó. Khi tiến trình đó tắt, kể cả tắt đột ngột, Chrome riêng và tiến trình nền của browser-harness tắt theo, không để sót.
