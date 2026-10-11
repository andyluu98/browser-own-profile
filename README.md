# browser-own-profile

Điều khiển **chính Chrome của bạn** (đã đăng nhập sẵn) bằng code hoặc bằng Claude Code: đọc sản phẩm Shopee, đọc bình luận một video TikTok, đăng video lên TikTok Studio, đăng bài Facebook. Chạy bằng [browser-harness](https://github.com/browser-use/browser-harness) (cùng công cụ với jev-ultrafast).

Bộ này **không lách** cơ chế chống bot. Nó chạy được vì dùng profile đã đăng nhập và làm với lượng nhỏ, giống người dùng thật. Gặp captcha thì nó **dừng và báo**, không giải hộ. Đọc [docs/03](docs/03_vi-sao-bi-chan.md) để hiểu vì sao.

## Bắt đầu trong 10 phút

Cần Windows, Google Chrome, Python 3.11 trở lên.

```bat
cd /d F:\GitHub\browser-own-profile
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

**1. Đăng nhập một lần** trong Chrome riêng của bộ công cụ (Chrome mở như bình thường, bạn tự đăng nhập, xong thì đóng hẳn cửa sổ):

```bat
cd /d F:\GitHub\browser-own-profile
.venv\Scripts\python -m browser_kit login --site shopee
```

**2. Chạy thử:**

```bat
cd /d F:\GitHub\browser-own-profile
.venv\Scripts\python -m browser_kit shopee --keyword "bàn phím" --min 800000 --max 1200000 --limit 10
```

Kết quả in ra màn hình và lưu ở `output\NN_shopee-ban-phim.csv` (mở bằng Excel được).

## Các lệnh

| Lệnh | Làm gì | Trạng thái |
|---|---|---|
| `login --site <trang>` | Mở Chrome riêng để bạn đăng nhập | Đã chạy thật |
| `check --site <trang>` | Mở trang, in các nút và ô công cụ nhìn thấy | Đã chạy thật |
| `shopee --keyword ... --min ... --max ... --limit 10` | Sản phẩm bán chạy, tối đa 20 | Đã chạy thật 12/10/2026 |
| `tiktok-comments --url <link video> --limit 30 --main` | Bình luận một video, tối đa 50 | Đã đọc được bằng Chrome chính 12/10/2026 |
| `tiktok-post --video clip.mp4 --caption "..."` | Đăng video của bạn qua TikTok Studio, **hỏi trước khi bấm Post** | Chưa đăng thật lần nào |
| `facebook-post --text "..."` | Đăng bài chữ lên Facebook của bạn, **hỏi trước khi bấm Đăng** | Chưa đăng thật lần nào |

Các trang có sẵn: `tiktok`, `tiktok-studio`, `facebook`, `shopee`, `google` (sửa trong `browser_kit/sites.json`).

`--main` dùng Chrome chính đang mở của bạn thay cho Chrome riêng. Chrome sẽ hỏi "Allow remote debugging?" mỗi lần chạy, bạn bấm Allow. Xem [docs/02](docs/02_chon-profile.md) để chọn.

## Tài liệu

1. [Cơ chế hoạt động](docs/01_co-che-hoat-dong.md): công cụ "nhìn" trang bằng cách nào, vì sao không cần chụp màn hình.
2. [Chọn profile](docs/02_chon-profile.md): Chrome riêng hay Chrome chính.
3. [Vì sao bị chặn](docs/03_vi-sao-bi-chan.md): captcha, profile mới, làm quá nhiều; bị chặn thì làm gì.
4. [An toàn](docs/04_an-toan.md): những gì bộ công cụ tự chặn để bảo vệ tài khoản của bạn.
5. [Xử lý lỗi](docs/05_xu-ly-loi.md): các lỗi đã gặp thật và cách sửa.

Dùng với Claude Code: chép thư mục này vào máy, Claude Code đọc [SKILL.md](SKILL.md) để biết cách dùng.

## Kiểm tra

```bat
cd /d F:\GitHub\browser-own-profile
.venv\Scripts\python -m unittest discover -s tests
```

Test chạy Chrome ẩn trên các trang mẫu trong máy, không ra mạng.
