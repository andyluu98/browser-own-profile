"""Command line.

  python -m browser_kit login --site shopee            sign in once in the separate profile (plain Chrome)
  python -m browser_kit check --site tiktok [--main]   open a site, show what the tool sees, close
  python -m browser_kit shopee --keyword "bàn phím" --min 800000 --max 1200000 --limit 10
  python -m browser_kit tiktok-comments --url <video link> --limit 30 --main
  python -m browser_kit tiktok-post --video clip.mp4 --caption "..."     (asks before Post)
  python -m browser_kit facebook-post --text "..." [--main]              (asks before Post)

--main uses your own running Chrome (turn on chrome://inspect/#remote-debugging, click Allow once per run).
Without it, the separate profile in %LOCALAPPDATA%\\browser-own-profile\\chrome is used (no prompt).
"""

import argparse
import csv
import datetime
import pathlib
import re
import subprocess
import sys
import unicodedata

from . import parse, recipes
from .guard import SITES, Blocked, Declined, Kit, fold
from .worker import default_profile, find_chrome

OUTPUT = pathlib.Path.cwd() / "output"
LOGS = pathlib.Path.cwd() / "logs"


def next_path(slug, ext):
    """output/NN_slug.ext with NN = highest existing number + 1 (any extension)."""
    OUTPUT.mkdir(exist_ok=True)
    nums = [int(m.group(1)) for p in OUTPUT.iterdir() if (m := re.match(r"(\d{2,3})_", p.name))]
    plain = unicodedata.normalize("NFD", fold(slug).replace("đ", "d"))
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")[:40] or "ket-qua"
    return OUTPUT / f"{max(nums, default=0) + 1:02d}_{slug}.{ext}"


def save_rows(rows, slug, raw_text):
    if not rows:  # keep the raw page text so the parser can be fixed (docs/05)
        path = next_path(slug + "-raw", "txt")
        path.write_text(raw_text, encoding="utf-8")
        print(f"Không tách được dòng nào. Đã lưu chữ thô của trang để kiểm tra: {path}")
        return
    path = next_path(slug, "csv")
    with path.open("w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel shows Vietnamese right
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Đã lưu {len(rows)} dòng: {path}")


def doctor():
    """What a helper (person or Claude Code) needs to know before running anything."""
    import importlib.util
    import platform
    ok = True
    print(f"Python {platform.python_version()} ({sys.executable})")
    if sys.version_info < (3, 11):
        ok = False
        print("  CHƯA ĐẠT: cần Python 3.11 trở lên (https://www.python.org/downloads/)")
    try:
        print(f"Chrome: {find_chrome()}")
    except RuntimeError as e:
        ok = False
        print(f"  CHƯA ĐẠT: {e} (cài Google Chrome)")
    if importlib.util.find_spec("browser_harness") is None:
        ok = False
        print(r"  CHƯA ĐẠT: thiếu thư viện, chạy: .venv\Scripts\python -m pip install -r requirements.txt")
    else:
        print("browser-harness: đã cài")
    profile = default_profile()
    used = (profile / "Default").is_dir()
    print(f"Chrome riêng: {profile} ({'đã từng mở' if used else 'chưa dùng lần nào, cần login'})")
    print("SẴN SÀNG" if ok else "CHƯA SẴN SÀNG")
    return ok


def login(site, wait=True):
    if site not in SITES:
        sys.exit(f"Không có trang '{site}'. Các trang có: {', '.join(sorted(SITES))}")
    profile = default_profile()
    profile.mkdir(parents=True, exist_ok=True)
    # Plain Chrome, nothing attached: you sign in exactly like a normal user.
    proc = subprocess.Popen([find_chrome(), f"--user-data-dir={profile}", "--no-first-run",
                             "--no-default-browser-check", SITES[site]["url"]])
    print(f"Đã mở {SITES[site]['name']} trong Chrome riêng ({profile}).")
    if not wait:  # a helper (Claude Code) asks the person to log in and close the window
        print("Đăng nhập xong thì ĐÓNG HẲN cửa sổ Chrome đó (cả các tab của nó).")
        return
    print("Đăng nhập xong thì ĐÓNG HẲN cửa sổ Chrome đó (cả các tab của nó). Đang chờ...")
    try:
        proc.wait()
    except KeyboardInterrupt:
        pass
    print("Xong. Các lệnh sau sẽ dùng phiên đăng nhập này.")


def make_ask(pre_confirmed):
    """Typed answer when a person is at the keyboard. Run by a helper without a keyboard (Claude Code):
    --yes means the person already confirmed this exact post in the chat; without it, refuse."""
    def ask(question):
        if not pre_confirmed and sys.stdin is not None and sys.stdin.isatty():
            try:
                return input(question)
            except EOFError:  # NUL on Windows looks like a terminal but has nobody typing
                pass
        if pre_confirmed:
            print(f"{question}có (đã xác nhận trước bằng --yes)")
            return "có"
        print(question)
        print("CẦN XÁC NHẬN: hỏi người dùng, họ đồng ý thì chạy lại lệnh với --yes")
        return "không"
    return ask


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="python -m browser_kit")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="kiểm tra máy đã sẵn sàng chưa")
    p = sub.add_parser("login", help="đăng nhập một lần trong Chrome riêng")
    p.add_argument("--site", required=True)
    p.add_argument("--no-wait", action="store_true", help="mở Chrome rồi trả lời ngay, không chờ đóng cửa sổ")
    p = sub.add_parser("check", help="mở trang, in những gì công cụ thấy")
    p.add_argument("--site", required=True)
    p = sub.add_parser("shopee", help="sản phẩm bán chạy trên Shopee")
    p.add_argument("--keyword", required=True)
    p.add_argument("--min", type=int)
    p.add_argument("--max", type=int)
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("tiktok-comments", help="bình luận của một video TikTok")
    p.add_argument("--url", required=True)
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--an-ten", action="store_true", help="đổi tên người bình luận thành Người 1, Người 2...")
    p = sub.add_parser("tiktok-post", help="đăng video của bạn qua TikTok Studio (hỏi trước khi đăng)")
    p.add_argument("--yes", action="store_true", help="người dùng đã xác nhận nội dung này (khi không gõ được)")
    p.add_argument("--video", required=True)
    p.add_argument("--caption", required=True)
    p = sub.add_parser("facebook-post", help="đăng bài chữ lên Facebook của bạn (hỏi trước khi đăng)")
    p.add_argument("--yes", action="store_true", help="người dùng đã xác nhận nội dung này (khi không gõ được)")
    p.add_argument("--text", required=True)
    p.add_argument("--image", help="đường dẫn một file ảnh kèm theo bài")
    for name, sp in sub.choices.items():
        if name not in ("login", "doctor"):
            sp.add_argument("--main", action="store_true", help="dùng Chrome chính đang mở (Chrome hỏi Allow)")
    args = ap.parse_args(argv)

    if args.cmd == "doctor":
        sys.exit(0 if doctor() else 1)
    if args.cmd == "login":
        return login(args.site, wait=not args.no_wait)
    log_file = LOGS / f"{datetime.datetime.now():%y%m%d-%H%M%S}_{args.cmd}.log"
    try:
        with Kit(main=args.main, ask=make_ask(getattr(args, "yes", False)), log_file=log_file) as kit:
            if args.cmd == "check":
                if args.site not in SITES:
                    sys.exit(f"Không có trang '{args.site}'. Các trang có: {', '.join(sorted(SITES))}")
                page = kit.open(SITES[args.site]["url"])
                snap = kit.snapshot()
                print(f"Mở được: {page['title']!r}. Thấy {len(snap['elements'])} nút và ô, ví dụ:")
                for e in snap["elements"][:12]:
                    print(f"  {e['kind']:6} {e.get('role', ''):9} {e.get('name', '')[:60]}")
            elif args.cmd == "shopee":
                rows, raw = recipes.shopee_search(kit, args.keyword, args.min, args.max, args.limit)
                for i, r in enumerate(rows, 1):
                    print(f"{i:2}. {r['price']}đ | {r['sold']} | {r['rating']} | {r['title'][:70]}")
                save_rows(rows, f"shopee-{args.keyword}", raw)
            elif args.cmd == "tiktok-comments":
                rows, raw = recipes.tiktok_comments(kit, args.url, args.limit)
                if args.an_ten:
                    rows = parse.anonymize(rows)
                for i, r in enumerate(rows, 1):
                    print(f"{i:2}. [{r['likes']} thích] {r['name']}: {r['comment'][:90]}")
                save_rows(rows, "tiktok-binh-luan", raw)
            elif args.cmd == "tiktok-post":
                print(recipes.tiktok_studio_post(kit, args.video, args.caption))
            elif args.cmd == "facebook-post":
                print(recipes.facebook_post(kit, args.text, args.image))
    except Blocked as e:
        print(f"Nhật ký: {log_file}")
        sys.exit(f"DỪNG: {e}")
    except Declined as e:
        print(f"Nhật ký: {log_file}")
        sys.exit(f"Đã hủy: {e}")
    except Exception as e:
        print(f"Nhật ký: {log_file}")
        sys.exit(f"Lỗi: {e}")
    print(f"Nhật ký: {log_file}")


if __name__ == "__main__":
    main()
