# 03. Vì sao bị chặn, và bị chặn thì làm gì

## Trang web nhận ra máy bằng cách nào

Các trang lớn chấm điểm "giống người hay giống máy" cho mỗi phiên, dựa trên nhiều dấu hiệu cùng lúc:

- **Lịch sử profile:** profile mới tinh, chưa từng lướt web, điểm thấp. Profile dùng lâu năm điểm cao.
- **Phiên đăng nhập:** chưa đăng nhập thì Shopee chuyển sang trang "Login Required", TikTok chỉ cho xem vài bình luận.
- **Loại dữ liệu:** dữ liệu trang muốn bảo vệ (bình luận, danh sách sản phẩm số lượng lớn) bị canh gắt hơn trang dành cho người tạo nội dung (TikTok Studio).
- **Khối lượng và tốc độ:** đọc hàng trăm trang mỗi phút thì chắc chắn bị chặn.
- **Kết nối điều khiển:** một số trang phát hiện được kết nối CDP. TikTok từng đóng băng trang ("Debugger paused") khi thấy dấu hiệu này.

Không ai đảm bảo được "không bao giờ dính captcha". Trang có thể đổi cách chấm điểm bất cứ lúc nào.

## Những gì bộ này làm, và không làm

**Làm:** dùng profile đã đăng nhập, đọc lượng nhỏ (giới hạn trong `guard.py`), một bài mỗi lần đăng. Đây là cách dùng bình thường của một người.

**Không làm:** giải captcha, giả dấu vân tay trình duyệt, cố ý rê chuột hay cuộn ngẫu nhiên để giả người, xoay vòng nhiều tài khoản, like hay comment hàng loạt. Đó là vượt rào: vi phạm điều khoản của nền tảng và là cách nhanh nhất để tài khoản bị khóa.

## Khi lệnh báo "DỪNG: Trang đang hỏi xác minh"

1. Không chạy lại ngay. Chạy lại liên tục làm điểm "giống máy" tệ hơn.
2. Mở trang đó trên Chrome như bình thường, tự xử lý nếu trang hỏi.
3. Nếu dùng Chrome riêng mà bị chặn, thử `--main` (Chrome chính, profile lâu năm).
4. Vẫn bị chặn: trang không cho đọc theo cách này. Cân nhắc API chính thức của nền tảng, hoặc tự sao chép bằng tay.

## Điều khoản và dữ liệu cá nhân

TikTok, Facebook, Shopee đều cấm thu thập dữ liệu tự động trong điều khoản sử dụng. Đọc lượng nhỏ cho việc cá nhân rủi ro thấp, nhưng tài khoản vẫn có thể bị hạn chế. Bình luận có tên người dùng: cẩn thận khi đưa vào tài liệu chia sẻ.
