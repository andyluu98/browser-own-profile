# 05. Xử lý lỗi (các lỗi đã gặp thật)

| Thông báo | Nguyên nhân | Cách sửa |
|---|---|---|
| "Chrome hồ sơ tự động đã mở sẵn hoặc không chạy được" | Cửa sổ Chrome lúc chạy `login` chưa đóng hẳn | Đóng mọi cửa sổ của Chrome đó; nếu Chrome chạy nền, bấm biểu tượng Chrome ở khay hệ thống rồi chọn Exit |
| "Trang yêu cầu đăng nhập" | Profile chưa đăng nhập trang đó | Chạy `login --site <trang>` |
| "DỪNG: Trang đang hỏi xác minh" | Trang nghi là máy | Xem [docs/03](03_vi-sao-bi-chan.md); thử `--main` |
| "Chrome chưa bật remote debugging" | Dùng `--main` nhưng chưa bật cho phép | Mở `chrome://inspect/#remote-debugging`, tick cho phép |
| Chrome hỏi Allow liên tục | Mỗi lần chạy `--main` là một kết nối mới | Bình thường. Dùng Chrome riêng nếu không muốn bấm |
| "Không tách được dòng nào", có file `-raw.txt` | Trang đổi bố cục | Đọc file raw, sửa mốc trong `browser_kit/parse.py`, thêm mẫu vào test |
| Bấm không ăn, báo hết thời gian chờ | Tab nằm nền không vẽ lại | Đã xử lý trong `worker.py` (giả lập tab đang được chọn); nếu vẫn gặp, báo lại kèm trang |

## Những recipe chưa chạy thật

`tiktok-post` và `facebook-post` viết theo bố cục trang đọc được ngày 12/10/2026 nhưng **chưa đăng thật lần nào**. Lần đầu dùng:

1. Chạy, đến bước hỏi "Bấm nút 'Post'?" thì gõ **không** để xem các bước trước có đúng không.
2. Đúng hết thì chạy lại và gõ **có**.
3. Báo lại chỗ sai (tên nút khác, không thấy ô mô tả...) để sửa recipe.
