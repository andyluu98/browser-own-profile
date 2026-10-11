# 02. Chọn profile: Chrome riêng hay Chrome chính

Profile là "một người dùng" trong Chrome: chứa cookie, phiên đăng nhập, lịch sử. Bộ này dùng được hai loại.

| | Chrome riêng (mặc định) | Chrome chính (`--main`) |
|---|---|---|
| Thư mục | `%LOCALAPPDATA%\browser-own-profile\chrome` | Profile Chrome bạn dùng hằng ngày |
| Đăng nhập | Một lần bằng lệnh `login --site <trang>` | Đã có sẵn |
| Hỏi "Allow remote debugging?" | Không | **Mỗi lần chạy**, bạn bấm Allow |
| Các tài khoản khác (Gmail, ngân hàng) | Không có trong profile này | Có, nên Chrome mới bắt hỏi Allow |
| Trang tin tưởng | Ít hơn (profile mới, ít lịch sử) | Nhiều hơn (dùng lâu năm) |

## Vì sao Chrome chính cứ hỏi Allow

Chrome chính đang đăng nhập đủ thứ. Nếu ai cũng kết nối vào được mà không hỏi, phần mềm độc hại có thể lặng lẽ chiếm tài khoản. Vì vậy từ Chrome 144, mỗi lần kết nối vào profile chính đều phải bấm Allow. Không có cài đặt nào tắt được, và bộ này không lách.

Bật cho phép một lần: mở `chrome://inspect/#remote-debugging` trong Chrome, tick ô cho phép.

## Kết quả thử thật (12/10/2026)

| Việc | Chrome riêng | Chrome chính |
|---|---|---|
| Shopee tìm sản phẩm | Chạy được sau khi `login --site shopee` | Chưa thử |
| TikTok Studio mở trang upload | Chạy được, không captcha | Chưa thử |
| TikTok đọc bình luận một video | **Bị captcha kéo thanh trượt** | Đọc được 35 bình luận |

Gợi ý: bắt đầu bằng Chrome riêng. Trang nào chặn profile mới thì mới dùng `--main`.

## Đổi thư mục Chrome riêng

Đặt biến `BOK_PROFILE` trỏ tới thư mục profile khác, ví dụ một profile đã đăng nhập sẵn:

```bat
cd /d F:\GitHub\browser-own-profile
set BOK_PROFILE=C:\Users\Ten\AppData\Local\profile-khac
.venv\Scripts\python -m browser_kit check --site shopee
```

Cửa sổ Chrome dùng profile đó phải **đóng hẳn** trước khi chạy lệnh.
