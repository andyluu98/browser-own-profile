# CLAUDE.md: hướng dẫn cho Claude Code trong repo này

Người dùng repo này thường **không biết mở terminal**. Claude Code tự chạy mọi lệnh; người dùng chỉ đăng nhập trên Chrome và trả lời "có/không". Không bảo người dùng tự gõ lệnh, trừ khi Claude Code không chạy được lệnh đó.

Mọi lệnh chạy trong thư mục repo bằng `.venv\Scripts\python -m browser_kit ...`.

## 1. Cài đặt (lần đầu, hoặc khi `doctor` báo chưa sẵn sàng)

1. Chưa có `.venv`: tạo bằng `py -3.12 -m venv .venv` (không có `py` thì dùng `python -m venv .venv`).
   Máy chưa có Python 3.11 trở lên: dừng lại, hướng dẫn người dùng tải từ https://www.python.org/downloads/ (tick "Add python.exe to PATH" khi cài), rồi làm tiếp.
2. `.venv\Scripts\python -m pip install -r requirements.txt`
3. `.venv\Scripts\python -m browser_kit doctor` phải in "SẴN SÀNG". Thiếu Chrome thì hướng dẫn cài Google Chrome.

Không cài Playwright, Puppeteer hay thư viện điều khiển trình duyệt nào khác khi chưa hỏi người dùng.

## 2. Đăng nhập: chỉ trang nào việc cần

Không bắt đăng nhập trước tất cả các trang. Chạy việc người dùng yêu cầu; nếu lệnh báo **"Trang yêu cầu đăng nhập"** thì:

1. Chạy `.venv\Scripts\python -m browser_kit login --site <trang> --no-wait` (trang: `shopee`, `tiktok`, `tiktok-studio`, `facebook`, `google`).
2. Nói với người dùng: "Em đã mở Chrome trang <tên>. Anh/chị đăng nhập, xong thì **đóng hẳn cửa sổ Chrome đó** rồi báo em."
3. Người dùng báo xong thì chạy lại việc lúc nãy. Nếu lệnh báo "Chrome hồ sơ tự động đã mở sẵn": cửa sổ chưa đóng hẳn, nhắc người dùng đóng (cả biểu tượng Chrome ở khay hệ thống, chọn Exit).

## 3. Yêu cầu thường gặp

| Người dùng nói | Lệnh |
|---|---|
| "Tìm 10 bàn phím bán chạy tầm 1 triệu trên Shopee" | `shopee --keyword "bàn phím" --min 800000 --max 1200000 --limit 10` |
| "Đọc bình luận video TikTok này <link>" | `tiktok-comments --url "<link>" --limit 30` (bị chặn thì hỏi người dùng có muốn thử `--main` không) |
| "Đăng video này lên TikTok, caption ..." | `tiktok-post --video "<đường dẫn>" --caption "..."` |
| "Đăng bài Facebook: ..." | `facebook-post --text "..."` |
| "Mở thử trang X xem được không" | `check --site <trang>` |

Khoảng giá mơ hồ ("tầm 1 triệu"): tự chọn khoảng hợp lý (ví dụ 800.000 đến 1.200.000) và nói rõ đã chọn gì.

**Đăng bài luôn cần người dùng đồng ý.** Khi Claude Code chạy (không có bàn phím), lệnh đi tới nút Đăng rồi in "CẦN XÁC NHẬN" và không bấm. Khi đó:
1. Hỏi người dùng trong khung chat, nêu rõ: trang nào, nội dung hoặc caption, file video.
2. Người dùng trả lời rõ là đồng ý thì chạy lại đúng lệnh đó, thêm `--yes`. Bất kỳ câu trả lời nào khác (im lặng, "để xem", "chắc vậy") đều là không.
3. Không bao giờ tự thêm `--yes` khi chưa hỏi, và không dùng một lần đồng ý cho bài khác.

`--main` (Chrome chính đang mở): chỉ dùng khi người dùng đồng ý. Người dùng phải bật `chrome://inspect/#remote-debugging` một lần và bấm Allow mỗi lần chạy. Không chạy `--main` nhiều lần liên tiếp.

## 4. Báo kết quả

- Trình bày thành bảng, kèm đường dẫn file CSV trong `output\`.
- Số "đã bán" của Shopee là nhãn làm tròn (8k+), không phải số chính xác.
- Có file `output\NN_...-raw.txt` nghĩa là trang đổi bố cục: báo người dùng, rồi sửa `browser_kit/parse.py` nếu được yêu cầu.

## 5. Ranh giới bắt buộc

- Lệnh báo **"DỪNG: Trang đang hỏi xác minh"**: dừng, báo người dùng. Không giải captcha, không chạy lại liên tục, không viết thêm code để né (giả chuột, giả dấu vân tay, đổi tài khoản).
- Không like hay comment hàng loạt; không tăng `LIMITS` trong `browser_kit/guard.py` khi chưa giải thích rủi ro cho người dùng.
- Không đọc, không gửi đi thư mục profile Chrome (`%LOCALAPPDATA%\browser-own-profile\chrome`): nó chứa phiên đăng nhập.
- Không đưa thư mục `output\` lên GitHub công khai.
