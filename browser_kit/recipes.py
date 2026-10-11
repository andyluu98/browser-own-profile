"""Ready-made tasks. Each one reads or posts a small, bounded amount and stops on verification pages.

Status (12/10/2026): shopee_search and tiktok_comments were run on the real sites; tiktok_studio_post and
facebook_post were written from the page layouts and still need a first real run (see docs/05).
"""

import os
import time
from urllib.parse import quote

from . import parse
from .guard import LIMITS, SITES, Blocked, find, fold


def _cap(n, key):
    return max(1, min(int(n), LIMITS[key]))


def shopee_search(kit, keyword, min_price=None, max_price=None, limit=10):
    """Top-selling Shopee products for a keyword (read only). Needs `login --site shopee` first."""
    limit = _cap(limit, "shopee_products")
    url = f"https://shopee.vn/search?keyword={quote(keyword)}&sortBy=sales&order=desc"
    if min_price:
        url += f"&minPrice={int(min_price)}"
    if max_price:
        url += f"&maxPrice={int(max_price)}"
    kit.open(url, settle=5)
    text = kit.read_text()
    return parse.shopee_products(text, limit), text


def tiktok_comments(kit, video_url, limit=30):
    """Top-level comments of ONE TikTok video (read only). Works best with main=True (your own Chrome)."""
    limit = _cap(limit, "tiktok_comments")
    if not video_url.startswith("https://www.tiktok.com/"):
        raise ValueError("cần link video TikTok dạng https://www.tiktok.com/@kenh/video/...")
    kit.open(video_url, settle=4)
    snap = kit.snapshot()
    tabs = find(snap, kind="click", names=("Comments", "Bình luận"))
    tabs = [e for e in tabs if e.get("role") in ("button", "tab")]
    if tabs:  # switches the side panel only; nothing is sent
        kit.note("bấm", f"tab '{tabs[0]['name']}' (chỉ đổi khung hiển thị)")
        kit.browser.click(tabs[0]["id"], expect_name=tabs[0]["name"])
        time.sleep(3)
    text = kit.read_text()
    rows = parse.tiktok_comments(text, limit)
    for _ in range(LIMITS["scroll_rounds"]):
        if len(rows) >= limit:
            break
        snap = kit.snapshot()
        # Scroll over an element that sits inside the comment list (a reply link), not the video area.
        anchors = [e for e in snap["elements"] if parse.VIEW_REPLIES.match(e.get("name", ""))
                   or parse.REPLY.match(e.get("name", ""))]
        if not anchors:
            break
        kit.scroll(anchors[-1], times=5)
        text = kit.read_text()
        more = parse.tiktok_comments(text, limit)
        if len(more) <= len(rows):
            break
        rows = more
    return rows, text


def tiktok_studio_post(kit, video_path, caption, upload_timeout=300):
    """Upload YOUR video in TikTok Studio, fill the caption, ask before pressing Post. One post per run."""
    if not os.path.isfile(video_path):
        raise ValueError(f"không thấy file video: {video_path}")
    kit.open(SITES["tiktok-studio"]["url"], settle=4)
    snap = kit.snapshot()
    inputs = find(snap, kind="upload")
    if not inputs:
        raise Blocked("không thấy ô chọn video trên TikTok Studio (chưa đăng nhập hoặc trang đã đổi)")
    kit.upload(inputs[0], os.path.abspath(video_path))

    def caption_box(s):
        boxes = [e for e in find(s, kind="fill") if e.get("role") == "textbox"
                 and "search" not in fold(e.get("name", ""))]
        return boxes[0] if boxes else None

    box = kit.wait_for(caption_box, timeout=60)
    if box is None:
        raise RuntimeError("không thấy ô mô tả sau khi tải video")
    kit.fill(box, caption)

    def post_button(s):
        ready = find(s, kind="click", names=("Post", "Đăng"), enabled=True)
        return ready[0] if ready else None

    button = kit.wait_for(post_button, timeout=upload_timeout, every=5)
    if button is None:
        raise RuntimeError("nút Post chưa bật (video chưa tải xong?)")
    kit.click(button, confirm_with=f"đăng video {os.path.basename(video_path)} lên TikTok")
    time.sleep(5)
    return kit.read_text()[:500]


def facebook_post(kit, text):
    """Post text on YOUR Facebook profile/feed, asking before pressing Post. One post per run."""
    kit.open(SITES["facebook"]["url"], settle=5)
    snap = kit.snapshot()
    openers = find(snap, kind="click", contains=("what's on your mind", "bạn đang nghĩ gì"))
    if not openers:
        raise Blocked("không thấy ô 'Bạn đang nghĩ gì?' (chưa đăng nhập Facebook hoặc trang đã đổi)")
    kit.note("bấm", f"'{openers[0]['name'][:40]}' (mở khung soạn bài)")
    kit.browser.click(openers[0]["id"], expect_name=openers[0]["name"])  # opens the composer only
    time.sleep(2)

    def composer(s):
        boxes = [e for e in find(s, kind="fill") if e.get("role") == "textbox"
                 and "search" not in fold(e.get("name", "")) and "tìm kiếm" not in fold(e.get("name", ""))]
        return boxes[-1] if boxes else None

    box = kit.wait_for(composer, timeout=15)
    if box is None:
        raise RuntimeError("không thấy ô soạn bài")
    kit.fill(box, text)
    time.sleep(1)

    def post_button(s):
        ready = find(s, kind="click", names=("Post", "Đăng"), enabled=True)
        return ready[-1] if ready else None

    button = kit.wait_for(post_button, timeout=15)
    if button is None:
        raise RuntimeError("không thấy nút Đăng")
    kit.click(button, confirm_with=f"đăng bài lên Facebook: '{text[:60]}'")
    time.sleep(4)
    return "đã bấm Đăng"
