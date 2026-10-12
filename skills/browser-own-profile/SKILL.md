---
name: browser-own-profile
description: Điều khiển Chrome đã đăng nhập của người dùng qua browser-harness để đăng video lên TikTok Studio, đăng bài Facebook (chữ, kèm một ảnh), đọc sản phẩm bán chạy trên Shopee, đọc bình luận một video TikTok. Dùng khi người dùng gọi "browser-own-profile" hoặc muốn tự động đăng video vừa làm lên TikTok/Facebook của họ, hay lấy dữ liệu Shopee/TikTok bằng tài khoản của chính họ. Không lách captcha, không like/comment hàng loạt.
---

# browser-own-profile

## Chạy lệnh

Thư mục gốc plugin = hai cấp trên thư mục của skill này (thư mục chứa `run.bat`, `run.sh`, `browser_kit\`).

- Windows: `"<gốc plugin>\run.bat" <lệnh> <tham số>`
- macOS: `"<gốc plugin>/run.sh" <lệnh> <tham số>`

Lần đầu `run` tự tạo môi trường Python và cài thư viện (mất 1 tới 2 phút). Môi trường, Chrome riêng, kết quả (`output\`) và nhật ký (`logs\`) nằm cố định ở `%LOCALAPPDATA%\browser-own-profile\` (macOS: `~/Library/Application Support/browser-own-profile/`), cập nhật plugin không làm mất.

Lệnh `run ... doctor` phải in "SẴN SÀNG". Báo "CHƯA CÓ PYTHON" thì hướng dẫn người dùng cài Python 3.11+ (tick "Add python.exe to PATH"), rồi chạy lại.

## Lệnh

| Người dùng muốn | Lệnh |
|---|---|
| Đăng video vừa làm lên TikTok | `tiktok-post --video "<đường dẫn tuyệt đối .mp4>" --caption "..."` |
| Đăng bài Facebook (có thể kèm ảnh) | `facebook-post --text "..." [--image "<đường dẫn ảnh>"]` |
| Sản phẩm bán chạy Shopee | `shopee --keyword "..." [--min 800000 --max 1200000] --limit 10` |
| Bình luận một video TikTok | `tiktok-comments --url "<link>" --limit 30 --main [--an-ten]` |
| Thử mở một trang | `check --site <tiktok, tiktok-studio, facebook, shopee, google>` |
| Đăng nhập một trang | `login --site <trang> --no-wait` |

Đường dẫn file luôn là đường dẫn tuyệt đối. Khoảng giá mơ hồ ("tầm 1 triệu"): tự chọn khoảng hợp lý và nói rõ.

## Quy trình

1. **Đăng nhập khi cần.** Lệnh báo "Trang yêu cầu đăng nhập" (hoặc không thấy ô chọn video, ô soạn bài vì chưa đăng nhập): chạy `login --site <trang> --no-wait`, nhờ người dùng đăng nhập trong cửa sổ Chrome vừa mở rồi **đóng hẳn cửa sổ đó**, chờ họ báo xong, chạy lại việc lúc nãy. Báo "Chrome hồ sơ tự động đã mở sẵn" nghĩa là cửa sổ chưa đóng hẳn (kể cả biểu tượng Chrome ở khay hệ thống, chọn Exit).
2. **Đăng bài luôn hỏi người dùng.** Lần chạy đầu không có `--yes`: lệnh đi tới nút Đăng rồi in "CẦN XÁC NHẬN" và không bấm. Hỏi người dùng trong chat, nêu rõ trang, nội dung hoặc caption, file. Họ đồng ý rõ ràng thì chạy lại **đúng lệnh đó** thêm `--yes`. Câu trả lời khác (im lặng, "chắc vậy", "để xem") là không. Không tự thêm `--yes`, không dùng một lần đồng ý cho bài khác.
3. **Báo kết quả** kèm đường dẫn file CSV hoặc file nhật ký mới nhất (dòng "Nhật ký: ..." cuối lệnh). Có lỗi thì đọc nhật ký trước khi đoán.

## Chọn Chrome

- Mặc định: Chrome riêng của bộ này, không hỏi Allow. Dùng cho TikTok Studio, Facebook, Shopee.
- `--main`: Chrome chính đang mở; người dùng bật `chrome://inspect/#remote-debugging` một lần và bấm Allow **mỗi lần chạy**. Bắt buộc cho đọc bình luận TikTok (Chrome riêng bị TikTok trả khung trống). Chỉ dùng khi người dùng đồng ý, không chạy liên tiếp nhiều lần.

## Ranh giới bắt buộc

- Lệnh báo **"DỪNG: Trang đang hỏi xác minh"**: dừng và báo người dùng. Không giải captcha, không chạy lại liên tục, không viết thêm code để né (giả chuột, giả dấu vân tay, đổi tài khoản).
- Không like hay comment hàng loạt, mỗi lần chạy một bài. Không tăng `LIMITS` trong `browser_kit/guard.py` khi chưa giải thích rủi ro.
- Không đọc, không gửi đi thư mục profile Chrome (chứa phiên đăng nhập).
- Không cài Playwright, Puppeteer hay thư viện điều khiển trình duyệt khác khi chưa hỏi.
- Skill `post-to-facebook` (Kimi WebBridge) là công cụ khác; chỉ dùng skill này khi người dùng gọi browser-own-profile hoặc cần các lệnh ở bảng trên.
