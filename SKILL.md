---
name: browser-own-profile
description: Điều khiển Chrome đã đăng nhập của người dùng qua browser-harness để đọc sản phẩm Shopee, đọc bình luận một video TikTok, đăng video lên TikTok Studio hoặc đăng bài Facebook. Dùng khi người dùng muốn tự động thao tác trên các trang này bằng tài khoản của chính họ. Không lách captcha, không like/comment hàng loạt.
---

# browser-own-profile

Bộ lệnh `python -m browser_kit` trong thư mục repo này. Chạy bằng `.venv\Scripts\python` của repo.

## Quy trình

0. **Lần đầu:** làm theo mục "Cài đặt" trong `CLAUDE.md` của repo; `doctor` phải in "SẴN SÀNG".
1. **Đăng nhập khi cần.** Nếu lệnh báo "yêu cầu đăng nhập", tự chạy
   `.venv\Scripts\python -m browser_kit login --site <trang> --no-wait`
   rồi nhờ người dùng đăng nhập và **đóng hẳn cửa sổ Chrome đó**, chờ họ báo xong.
2. **Chạy lệnh phù hợp** (xem README, bảng "Các lệnh"). Đọc dữ liệu thì dùng `shopee` hoặc `tiktok-comments`; đăng bài thì dùng `tiktok-post` hoặc `facebook-post`.
3. **Báo kết quả** kèm đường dẫn file CSV trong `output\`. Số "đã bán" của Shopee là nhãn làm tròn (8k+), không phải số chính xác.

## Chọn Chrome

- Mặc định: Chrome riêng của bộ công cụ, không hỏi Allow. Hợp với Shopee, TikTok Studio.
- `--main`: Chrome chính đang mở (người dùng bật `chrome://inspect/#remote-debugging`, bấm Allow mỗi lần chạy). Dùng khi trang chặn profile mới, ví dụ đọc bình luận TikTok. Không chạy `--main` nhiều lần liên tiếp vì mỗi lần người dùng phải bấm Allow.

## Ranh giới bắt buộc

- Lệnh báo **"DỪNG: Trang đang hỏi xác minh"** thì dừng, báo người dùng. **Không** giải captcha, không thử lại liên tục, không đổi cách để né, không giả thao tác người.
- Đăng bài, comment, like, mua, xóa: bộ công cụ tự hỏi "có/không" trước khi bấm. Chạy không có bàn phím thì lệnh in "CẦN XÁC NHẬN": hỏi người dùng trong chat, họ đồng ý rõ ràng thì chạy lại với `--yes`. Không tự thêm `--yes`. Mỗi lần chạy chỉ một bài.
- Không like hay comment hàng loạt, không nuôi nhiều tài khoản, không chạy vòng lặp đọc dữ liệu lớn. Giới hạn nằm ở `LIMITS` trong `browser_kit/guard.py`.
- Không cài thêm Playwright, Puppeteer hay thư viện điều khiển trình duyệt khác khi chưa hỏi người dùng.
- Không đọc, không gửi đi file trong thư mục profile Chrome (chứa phiên đăng nhập).

## Khi lệnh không tách được dữ liệu

Lệnh lưu chữ thô của trang vào `output\NN_...-raw.txt`. Trang đã đổi bố cục: đọc file đó, sửa các mốc trong `browser_kit/parse.py`, thêm mẫu vào `tests/test_guard_parse.py`, chạy test.
