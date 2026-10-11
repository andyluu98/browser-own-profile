"""Safety checks and text parsers: no browser needed. Sample texts mimic the real layouts with made-up data."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from browser_kit import guard, parse  # noqa: E402

SHOPEE = """Search result for 'bàn phím'
Sort by
Top Sales
1/6
Bàn phím cơ Mẫu A 3 mode hotswap
899.000
₫
919.000
₫
-2%
5.0
8k+ Sold/Month
Thành phố Hà Nội
Find Similar
Bàn phím Mẫu B không có giá gốc
949.000
₫
4.8
1k+ Sold/Month
Thành phố Hồ Chí Minh
Find Similar
CUSTOMER SERVICE
Help Centre"""

TIKTOK = """Comments
You may like
454 comments
Người A
Bình luận đầu tiên
9-22
Reply
1088
View 36 replies
Người B
dòng một
dòng hai
1d ago
Reply
0
Người C
9-23
Reply
5
Add comment..."""


class ParseTests(unittest.TestCase):
    def test_shopee_cards(self):
        rows = parse.shopee_products(SHOPEE, 10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"title": "Bàn phím cơ Mẫu A 3 mode hotswap", "price": "899.000",
                                   "original_price": "919.000", "rating": "5.0", "sold": "8k+ Sold/Month",
                                   "location": "Thành phố Hà Nội"})
        self.assertEqual(rows[1]["original_price"], "")

    def test_shopee_limit(self):
        self.assertEqual(len(parse.shopee_products(SHOPEE, 1)), 1)

    def test_tiktok_comments(self):
        rows = parse.tiktok_comments(TIKTOK, 50)
        self.assertEqual([r["name"] for r in rows], ["Người A", "Người B", "Người C"])
        self.assertEqual(rows[0]["replies"], "36")
        self.assertEqual(rows[0]["likes"], "1088")
        self.assertEqual(rows[1]["comment"], "dòng một dòng hai")
        self.assertEqual(rows[2]["comment"], "")  # sticker-only comment

    def test_shopee_vietnamese_labels(self):
        text = ("Bàn phím Mẫu C\n799.000\n₫\n4.9\nĐã bán 2,1k\nHà Nội\nTìm sản phẩm tương tự\n"
                "Bàn phím Mẫu D\n1.050.000\n₫\n5.0\nĐã bán 120\nTP. Hồ Chí Minh\nTìm sản phẩm tương tự\n")
        rows = parse.shopee_products(text, 10)
        self.assertEqual([(r["title"], r["sold"]) for r in rows],
                         [("Bàn phím Mẫu C", "Đã bán 2,1k"), ("Bàn phím Mẫu D", "Đã bán 120")])

    def test_anonymize_keeps_same_person_same_label(self):
        rows = [{"name": "A", "comment": "1"}, {"name": "B", "comment": "2"}, {"name": "A", "comment": "3"}]
        self.assertEqual([r["name"] for r in parse.anonymize(rows)], ["Người 1", "Người 2", "Người 1"])
        self.assertEqual(rows[0]["name"], "A")  # input untouched

    def test_tiktok_no_panel(self):
        self.assertEqual(parse.tiktok_comments("For You\nExplore", 10), [])


class GuardTests(unittest.TestCase):
    def test_captcha_stops(self):
        for url, text in (("https://x/", "Drag the slider to fit the puzzle"),
                          ("https://shopee.vn/verify/traffic/error", "Something"),
                          ("https://x/", "Vui lòng kéo thanh trượt")):
            with self.subTest(text=text), self.assertRaises(guard.Blocked):
                guard.check_page(url, text)

    def test_login_wall_says_login(self):
        with self.assertRaises(guard.Blocked) as cm:
            guard.check_page("https://shopee.vn/verify/traffic/error", "Login Required\nLog in to continue")
        self.assertIn("đăng nhập", str(cm.exception))

    def test_normal_page_passes(self):
        guard.check_page("https://shopee.vn/search", "Bàn phím cơ 899.000 ₫")

    def test_only_explicit_yes(self):
        for answer, ok in (("có", True), ("y", True), ("Có ", True), ("không", False), ("", False),
                           ("có lẽ", False), ("ok", False)):
            with self.subTest(answer=answer):
                self.assertIs(guard.ask_yes("?", ask=lambda _: answer), ok)

    def test_risky_names(self):
        for name in ("Post", "Đăng", "Like video", "Gửi", "Mua ngay"):
            self.assertTrue(guard.is_risky(name), name)
        self.assertFalse(guard.is_risky("Xem thêm"))

    def test_click_on_risky_button_needs_yes(self):
        kit = guard.Kit.__new__(guard.Kit)
        kit.ask = lambda _: "không"

        class NoBrowser:
            def click(self, *a, **k):
                raise AssertionError("must not click")

        kit.browser = NoBrowser()
        with self.assertRaises(guard.Declined):
            kit.click({"id": "e1", "name": "Đăng"})

    def test_log_never_has_filled_text(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            kit = guard.Kit.__new__(guard.Kit)
            kit.log_file = pathlib.Path(tmp, "run.log")

            class FakeBrowser:
                def fill(self, *a):
                    return {}

            kit.browser = FakeBrowser()
            kit.fill({"id": "e1", "name": "Mô tả"}, "nội dung bí mật")
            log = kit.log_file.read_text(encoding="utf-8")
        self.assertIn("ô 'Mô tả' (15 ký tự)", log)
        self.assertNotIn("bí mật", log)

    def test_limits_capped(self):
        from browser_kit import recipes
        self.assertEqual(recipes._cap(500, "tiktok_comments"), guard.LIMITS["tiktok_comments"])
        self.assertEqual(recipes._cap(0, "shopee_products"), 1)


if __name__ == "__main__":
    unittest.main()
