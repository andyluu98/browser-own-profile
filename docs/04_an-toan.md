# 04. An toàn: bộ công cụ tự chặn những gì

| Chốt | Ở đâu | Làm gì |
|---|---|---|
| Dừng khi gặp captcha hoặc tường đăng nhập | `guard.check_page` | Mỗi lần đọc trang đều kiểm tra; thấy chữ như "Drag the slider", đường dẫn `/verify/` thì dừng |
| Hỏi trước nút rủi ro | `guard.Kit.click` | Nút có chữ Post, Đăng, Like, Gửi, Mua, Xóa, Follow... phải gõ "có" mới bấm. "có lẽ", "ok", bỏ trống đều tính là không |
| Kiểm tên nút lúc bấm | `worker.cmd_click` | Tên hoặc chữ trên nút khác lúc đọc trang thì từ chối bấm |
| Giới hạn khối lượng | `guard.LIMITS` | Tối đa 20 sản phẩm, 50 bình luận, 4 vòng cuộn, 1 bài mỗi lần chạy |
| Ẩn dữ liệu nhạy cảm | `snapshot.js` | Mật khẩu, số thẻ, OTP, token không bao giờ có trong dữ liệu đọc ra |
| Chỉ mở https | `worker.cmd_open` | Không mở http, javascript:, ftp |
| Chỉ dùng tab của mình | `worker.py` | Với Chrome chính: không đọc, không chuyển sang, không đóng tab khác của bạn, không đóng Chrome |
| Tắt gửi số liệu | `worker.py` | browser-harness mặc định gửi số liệu sử dụng về Browser Use; bộ này luôn tắt (`BH_TELEMETRY=0`) và không dùng dịch vụ cloud của họ |

## Bạn cần tự giữ

- **Không chia sẻ thư mục profile** (`%LOCALAPPDATA%\browser-own-profile\chrome`): ai có thư mục này là có phiên đăng nhập của bạn.
- **Không đưa thư mục `output\`** lên GitHub công khai nếu có dữ liệu người khác (đã có trong `.gitignore`).
- Muốn nới giới hạn trong `LIMITS` thì hiểu rõ rủi ro ở [docs/03](03_vi-sao-bi-chan.md) trước.
