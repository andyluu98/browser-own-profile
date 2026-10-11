"""Safety layer over client.Browser.

- Stops as soon as a page shows a verification check (captcha, slider, "verify"): never solves or evades it.
- Asks the person before any click that publishes, sends, likes, buys or deletes.
- Hard limits on how much one run may read or post.
"""

import json
import pathlib
import time
import unicodedata

from .client import Browser

SITES = {k: v for k, v in json.loads(
    pathlib.Path(__file__).with_name("sites.json").read_text(encoding="utf-8")).items()}

# Words that mean "the site wants to check you are human". Lower-case, compared on folded page text.
BLOCK_WORDS = ("drag the slider", "fit the puzzle", "captcha", "verify you are human", "verify to continue",
               "kéo thanh trượt", "xác minh bạn", "xác minh để tiếp tục", "security check")
BLOCK_URL_PARTS = ("/verify/", "/captcha", "/checkpoint/")
LOGIN_WORDS = ("login required", "log in to continue", "đăng nhập để tiếp tục")

LIMITS = {
    "shopee_products": 20,  # products per search
    "tiktok_comments": 50,  # top-level comments per video
    "scroll_rounds": 4,  # each round = up to 5 wheel notches inside the worker
    "posts_per_run": 1,  # one post / comment / like per command, always confirmed
}

RISKY_WORDS = ("post", "đăng", "publish", "share", "chia sẻ", "send", "gửi", "comment", "bình luận", "like",
               "thích", "buy", "mua", "đặt hàng", "thanh toán", "delete", "xóa", "follow", "theo dõi")


class Blocked(RuntimeError):
    """The site shows a verification check or asks to log in: stop, a person must handle it."""


class Declined(RuntimeError):
    """The person said no at a confirmation."""


def fold(s):
    return " ".join(unicodedata.normalize("NFC", s or "").split()).casefold()


def check_page(url, text):
    t, u = fold(text), (url or "").lower()
    if any(p in u for p in BLOCK_URL_PARTS) or any(w in t for w in BLOCK_WORDS):
        if any(w in t for w in LOGIN_WORDS):
            raise Blocked("Trang yêu cầu đăng nhập: chạy lệnh login cho trang này rồi thử lại")
        raise Blocked("Trang đang hỏi xác minh (captcha). Dừng lại: không giải hộ, không lách. "
                      "Anh/chị tự xử lý trên trình duyệt hoặc thử lại sau, làm ít hơn.")
    if any(w in t for w in LOGIN_WORDS):
        raise Blocked("Trang yêu cầu đăng nhập: chạy lệnh login cho trang này rồi thử lại")


def is_risky(name):
    n = fold(name)
    return any(w in n for w in RISKY_WORDS)


def ask_yes(question, ask=input):
    """Typed yes/no. Only an explicit yes counts."""
    answer = fold(ask(f"{question} (có/không): "))
    return answer in {"có", "co", "c", "yes", "y"}


def find(snap, kind=None, names=(), contains=(), enabled=None):
    """Elements of a snapshot by kind and name (exact names, or folded substrings)."""
    want = {fold(n) for n in names}
    parts = [fold(c) for c in contains]
    out = []
    for e in snap.get("elements", []):
        if kind and e["kind"] != kind:
            continue
        n = fold(e.get("name", ""))
        if want and n not in want:
            continue
        if parts and not any(p in n for p in parts):
            continue
        if enabled is not None and e.get("disabled") is enabled:
            continue
        out.append(e)
    return out


class Kit:
    """Browser + checks. main=True: the person's own running Chrome (Chrome asks Allow once per run);
    main=False: the separate profile created by `login` (no prompt)."""

    def __init__(self, main=False, headless=False, profile_dir=None, ask=input, log=print):
        self.browser = Browser(profile_dir=profile_dir, headless=headless, attach=main)
        self.ask, self.log = ask, log

    def __enter__(self):
        self.browser.start()
        return self

    def __exit__(self, *exc):
        self.browser.close()

    def open(self, url, settle=3.0):
        page = self.browser.open(url)
        time.sleep(settle)
        self.snapshot()  # checks for verification pages
        return page

    def snapshot(self):
        snap = self.browser.snapshot()
        check_page(snap.get("url", ""), snap.get("text", ""))
        return snap

    def read_text(self):
        snap = self.browser.snapshot()
        text = self.browser.read_text()
        check_page(snap.get("url", ""), text)
        return text

    def click(self, el, confirm_with=None):
        """Click a snapshot element. Risky names (post, like, send...) are confirmed first, showing the real
        button name and page title; the click is refused if the button changed since the snapshot."""
        if confirm_with is not None or is_risky(el.get("name", "")):
            title = confirm_with or el.get("name", "")
            if not ask_yes(f"Bấm nút '{el.get('name', '')}' ({title})?", self.ask):
                raise Declined(f"Không bấm '{el.get('name', '')}' theo yêu cầu")
        r = self.browser.click(el["id"], expect_name=el.get("name", ""), expect_text=el.get("text") or None)
        time.sleep(1.0)
        self.snapshot()
        return r

    def fill(self, el, text):
        return self.browser.fill(el["id"], text)

    def upload(self, el, path):
        return self.browser.upload(el["id"], path)

    def scroll(self, el, times=5):
        return self.browser.scroll(el["id"], times=times)

    def wait_for(self, test, timeout, every=2.0):
        """Poll snapshots until test(snap) returns something truthy; checks each page for verification."""
        deadline = time.monotonic() + timeout
        while True:
            snap = self.snapshot()
            found = test(snap)
            if found:
                return found
            if time.monotonic() >= deadline:
                return None
            time.sleep(every)
