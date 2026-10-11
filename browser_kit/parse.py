"""Turn visible page text (read_text) into rows. Pure functions: tested on saved text, no browser needed.

The layouts below were read from the real pages on 12/10/2026. Sites change their pages; when a parser
returns nothing, look at the raw text (the recipes save it next to the CSV) and adjust the markers here.
"""

import re

PRICE = re.compile(r"^\d{1,3}(?:\.\d{3})+$")
RATING = re.compile(r"^[1-5]\.\d$")
SOLD = re.compile(r"(sold|đã bán)", re.I)
SHOPEE_END = re.compile(r"^(find similar|tìm sản phẩm tương tự)$", re.I)


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def shopee_products(text, limit):
    """Shopee search result cards: title, price, original price, rating, sold label, location."""
    out, block = [], []
    for line in _lines(text):
        if SHOPEE_END.match(line):
            row = _shopee_card(block)
            if row:
                out.append(row)
                if len(out) >= limit:
                    break
            block = []
        else:
            block.append(line)
    return out


def _shopee_card(lines):
    prices = [i for i, line in enumerate(lines) if PRICE.match(line)]
    sold = next((line for line in lines if SOLD.search(line)), None)
    if not prices or sold is None or prices[0] == 0:
        return None
    first = prices[0]
    sold_i = lines.index(sold)
    rating = next((line for line in lines[first:sold_i] if RATING.match(line)), "")
    return {
        "title": lines[first - 1],
        "price": lines[first],
        "original_price": lines[prices[1]] if len(prices) > 1 and prices[1] < sold_i else "",
        "rating": rating,
        "sold": sold,
        "location": lines[sold_i + 1] if sold_i + 1 < len(lines) else "",
    }


COMMENTS_HEADER = re.compile(r"^[\d.,]+[KkMm]?\s+(comments|bình luận)$", re.I)
COMMENTS_END = re.compile(r"^(add comment|thêm bình luận)", re.I)
REPLY = re.compile(r"^(reply|trả lời)$", re.I)
VIEW_REPLIES = re.compile(r"^(?:view|xem)\s+([\d.,]+[KkMm]?)\s+(?:repl(?:y|ies)|câu trả lời)", re.I)


def tiktok_comments(text, limit):
    """TikTok comment panel: name, comment, date, likes, replies. Block = name, text..., date, Reply, likes,
    [View N replies]."""
    lines = _lines(text)
    start = next((i + 1 for i, line in enumerate(lines) if COMMENTS_HEADER.match(line)), None)
    if start is None:
        return []
    end = next((i for i in range(start, len(lines)) if COMMENTS_END.match(lines[i])), len(lines))
    lines = lines[start:end]
    out, p, i = [], 0, 0
    while i < len(lines) and len(out) < limit:
        if REPLY.match(lines[i]):
            block = lines[p:i]
            likes = lines[i + 1] if i + 1 < len(lines) else ""
            nxt, replies = i + 2, "0"
            m = VIEW_REPLIES.match(lines[nxt]) if nxt < len(lines) else None
            if m:
                replies, nxt = m.group(1), nxt + 1
            if len(block) >= 2:
                out.append({"name": block[0], "comment": " ".join(block[1:-1]), "date": block[-1],
                            "likes": likes, "replies": replies})
            p = i = nxt
        else:
            i += 1
    return out


def anonymize(rows, key="name"):
    """Replace names with 'Người 1', 'Người 2'... (same person, same label) before saving or sharing."""
    labels = {}
    out = []
    for r in rows:
        label = labels.setdefault(r[key], f"Người {len(labels) + 1}")
        out.append({**r, key: label})
    return out
