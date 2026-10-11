"""Browser tests: real headless Chrome (channel chrome) on local fixtures via file://, no network."""

import importlib.util
import os
import pathlib
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from browser_kit.client import Browser, BrowserError  # noqa: E402
from browser_kit.worker import Worker  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
CHROME = pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
HAVE_CHROME = CHROME.exists() or bool(shutil.which("chrome"))

if not HAVE_CHROME:
    raise unittest.SkipTest("Chrome chưa cài (cần Google Chrome), bỏ qua test trình duyệt")
if importlib.util.find_spec("browser_harness") is None:
    raise unittest.SkipTest("chưa có công cụ điều khiển trình duyệt (cần browser-harness), bỏ qua test trình duyệt")


def fixture(name):
    return (FIXTURES / name).as_uri()


class BrowserCase(unittest.TestCase):
    """One headless Browser with a temporary profile per test class."""

    @classmethod
    def setUpClass(cls):
        cls.profile = tempfile.mkdtemp(prefix="bok-test-")
        cls.browser = Browser(profile_dir=cls.profile, headless=True)
        cls.browser.start()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        shutil.rmtree(cls.profile, ignore_errors=True)

    def find(self, snap, kind, name):
        for e in snap["elements"]:
            if e["kind"] == kind and name in e["name"]:
                return e
        self.fail(f"không thấy phần tử {kind} '{name}' trong {snap['elements']}")


class UploadFormTest(BrowserCase):
    def setUp(self):
        self.browser.open(fixture("upload_form.html"))

    def test_snapshot_elements(self):
        snap = self.browser.snapshot()
        self.assertEqual(snap["title"], "Đăng video")
        self.assertIn("Đăng video", snap["text"])
        self.assertLessEqual(len(snap["text"]), 4000)
        pick = self.find(snap, "click", "Chọn video")
        self.assertEqual(pick["role"], "button")
        desc = self.find(snap, "fill", "Mô tả")
        self.assertEqual(desc["role"], "textbox")
        up = self.find(snap, "upload", "Chọn video")
        ids = [e["id"] for e in snap["elements"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(up["id"].startswith("e"))

    def test_post_disabled_before_upload(self):
        snap = self.browser.snapshot()
        post = self.find(snap, "click", "Đăng")
        self.assertEqual(post["name"], "Đăng")
        self.assertIs(post["disabled"], True)
        self.assertEqual(post["text"], "Đăng")
        self.assertIs(self.find(snap, "fill", "Mô tả")["disabled"], False)
        for e in snap["elements"]:
            self.assertEqual(set(e), {"id", "kind", "role", "name", "text", "value", "sensitive",
                                      "placeholder", "disabled"})

    def test_fill_upload_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = os.path.join(tmp, "clip.mp4")
            with open(video, "wb") as f:
                f.write(b"\x00" * 64)
            snap = self.browser.snapshot()
            desc = self.find(snap, "fill", "Mô tả")
            self.browser.fill(desc["id"], "bản nháp")
            self.browser.fill(desc["id"], "Bàn phím cơ mới")  # must replace, not append
            self.browser.upload(self.find(snap, "upload", "Chọn video")["id"], video)
            snap = self.browser.snapshot()
            self.assertEqual(self.find(snap, "fill", "Mô tả")["value"], "Bàn phím cơ mới")
            post = self.find(snap, "click", "Đăng")
            self.assertIs(post["disabled"], False)
            self.browser.click(post["id"], expect_name="Đăng")
            self.assertIn("Đã đăng: clip.mp4", self.browser.read_text())

    def test_click_visible_pick_button(self):
        snap = self.browser.snapshot()
        r = self.browser.click(self.find(snap, "click", "Chọn video")["id"])
        self.assertTrue(r["ok"])
        self.assertIn("upload_form.html", r["url"])

    def test_upload_missing_file(self):
        snap = self.browser.snapshot()
        up = self.find(snap, "upload", "Chọn video")
        with self.assertRaises(BrowserError):
            self.browser.upload(up["id"], os.path.join(tempfile.gettempdir(), "khong-co-file.mp4"))

    def test_unknown_element(self):
        self.browser.snapshot()
        with self.assertRaises(BrowserError):
            self.browser.click("e999")
        with self.assertRaises(BrowserError):
            self.browser.click("div > a")  # only ids from snapshot are accepted

    def test_press_rejects_other_keys(self):
        with self.assertRaises(BrowserError):
            self.browser.press("F5")
        self.assertTrue(self.browser.press("Tab")["url"])


class PromptToolTest(BrowserCase):
    def setUp(self):
        self.browser.open(fixture("prompt_tool.html"))

    def test_prompt_flow(self):
        snap = self.browser.snapshot()
        self.browser.fill(self.find(snap, "fill", "Nhập prompt")["id"], "Quảng cáo bàn phím cơ")
        self.browser.click(self.find(snap, "click", "Tạo")["id"])
        self.assertIn("Đang tạo...", self.browser.read_text())
        deadline = 6
        t0 = time.time()
        while "Xong" not in self.browser.read_text():
            self.assertLess(time.time() - t0, deadline, "không thấy 'Xong'")
            time.sleep(0.3)

    def test_new_tab_followed(self):
        snap = self.browser.snapshot()
        r = self.browser.click(self.find(snap, "click", "Xem lịch sử")["id"])
        self.assertIn("second_page.html", r["url"])
        snap = self.browser.snapshot()
        self.assertEqual(snap["title"], "Lịch sử")
        self.assertIn("Lịch sử video", self.browser.read_text())
        self.find(snap, "click", "Quay lại")


class RenameGuardTest(BrowserCase):
    def test_click_refused_after_rename(self):
        self.browser.open(fixture("rename_button.html"))
        snap = self.browser.snapshot()
        btn = self.find(snap, "click", "Tiếp")
        time.sleep(1.3)  # the page renames the button to 'Đăng'
        with self.assertRaises(BrowserError) as cm:
            self.browser.click(btn["id"], expect_name="Tiếp")
        self.assertIn("phần tử đã đổi: 'Tiếp' -> 'Đăng'", str(cm.exception))
        self.assertNotIn("Đã bấm", self.browser.read_text())
        # same id, new name (whitespace/case folded): allowed
        self.browser.click(btn["id"], expect_name="  đăng ")
        self.assertIn("Đã bấm: Đăng", self.browser.read_text())

    def test_click_without_expect_name_unchanged(self):
        self.browser.open(fixture("rename_button.html"))
        btn = self.find(self.browser.snapshot(), "click", "Tiếp")
        self.browser.click(btn["id"])
        self.assertIn("Đã bấm", self.browser.read_text())


class AriaRenameGuardTest(BrowserCase):
    """L1: aria-label unchanged, visible text changed."""

    def test_click_refused_when_visible_text_changed(self):
        self.browser.open(fixture("aria_rename.html"))
        btn = self.find(self.browser.snapshot(), "click", "Next")
        self.assertEqual((btn["name"], btn["text"]), ("Next", "Next"))
        time.sleep(1.3)
        with self.assertRaises(BrowserError) as cm:
            self.browser.click(btn["id"], expect_name="Next", expect_text="Next")
        self.assertIn("chữ của phần tử đã đổi: 'Next' -> 'Post'", str(cm.exception))
        self.assertNotIn("Đã bấm", self.browser.read_text())
        self.browser.click(btn["id"], expect_name="Next", expect_text="")  # empty: not compared
        self.assertIn("Đã bấm: Post", self.browser.read_text())

    def test_click_allowed_when_text_same(self):
        self.browser.open(fixture("aria_rename.html"))
        time.sleep(1.3)
        btn = self.find(self.browser.snapshot(), "click", "Next")
        self.browser.click(btn["id"], expect_name="Next", expect_text="  post ")
        self.assertIn("Đã bấm: Post", self.browser.read_text())


class SecretsTest(BrowserCase):
    """N2: no secret value in snapshot() or read_text()."""
    SECRETS = ("S3cret-Pass", "4111111111111111", "918273", "tok-ABCDEF123")

    def setUp(self):
        self.browser.open(fixture("login.html"))

    def test_sensitive_values_hidden(self):
        snap = self.browser.snapshot()
        self.assertEqual(self.find(snap, "fill", "Tên đăng nhập")["value"], "anh-nam")
        sensitive = [e for e in snap["elements"] if e["sensitive"]]
        self.assertEqual(len(sensitive), 4)  # password, card, otp, token
        for e in sensitive:
            self.assertEqual(e["value"], "")
            self.assertEqual(e["text"], "")
        self.assertFalse(self.find(snap, "click", "Vào")["sensitive"])
        blob = repr(snap)
        for secret in self.SECRETS:
            self.assertNotIn(secret, blob)
            self.assertNotIn(secret, self.browser.read_text())

    def test_other_values_capped_at_80(self):
        note = self.find(self.browser.snapshot(), "fill", "Ghi chú")
        self.assertEqual(len(note["value"]), 80)


class RecoveryTest(unittest.TestCase):
    """N3: Chrome context closed under the worker: relaunch once."""

    def setUp(self):
        self.profile = tempfile.mkdtemp(prefix="bok-test-")
        self.b = Browser(profile_dir=self.profile, headless=True)
        self.b.start()

    def tearDown(self):
        self.b.close()
        shutil.rmtree(self.profile, ignore_errors=True)

    def test_open_recovers_after_pages_closed(self):
        self.b.open(fixture("second_page.html"))
        self.b._call("debug_close_pages")
        self.assertEqual(self.b.open(fixture("upload_form.html"))["title"], "Đăng video")
        self.assertEqual(self.b.snapshot()["title"], "Đăng video")

    def test_snapshot_recovers_after_pages_closed(self):
        self.b.open(fixture("second_page.html"))
        self.b._call("debug_close_pages")
        self.assertEqual(self.b.snapshot()["elements"], [])  # fresh blank page

    def test_click_reports_closed_page_then_works(self):
        self.b.open(fixture("rename_button.html"))
        btn = self.b.snapshot()["elements"][0]
        self.b._call("debug_close_pages")
        with self.assertRaises(BrowserError) as cm:
            self.b.click(btn["id"])
        self.assertIn("trang đã bị đóng, hãy mở lại trang", str(cm.exception))
        self.assertEqual(self.b.open(fixture("second_page.html"))["title"], "Lịch sử")

    def test_debug_command_refused_when_not_headless(self):
        w = Worker.__new__(Worker)
        w.headless = False
        with self.assertRaises(ValueError):
            w.cmd_debug_close_pages({})


class PopupFilterTest(BrowserCase):
    def test_blank_and_closed_popups_ignored(self):
        for name in ("Mở trống", "Mở rồi đóng"):
            with self.subTest(button=name):
                self.browser.open(fixture("popup_blank.html"))
                btn = self.find(self.browser.snapshot(), "click", name)
                r = self.browser.click(btn["id"])
                self.assertIn("popup_blank.html", r["url"])


class OpenRulesTest(BrowserCase):
    def test_rejects_http_and_other_schemes(self):
        for url in ("http://example.com", "javascript:alert(1)", "ftp://x/y", "example.com"):
            with self.subTest(url=url), self.assertRaises(BrowserError):
                self.browser.open(url)

    def test_file_url_rejected_when_not_headless(self):
        w = Worker.__new__(Worker)  # no Chrome needed: validation happens before any page access
        w.headless = False
        with self.assertRaises(ValueError):
            w.cmd_open({"url": fixture("upload_form.html")})
        with self.assertRaises(ValueError):
            w.cmd_open({"url": "http://example.com"})


class ScrollRulesTest(unittest.TestCase):
    def test_times_bounded(self):
        w = Worker.__new__(Worker)  # validation happens before any page access
        for times in (0, 6, "3", None):
            with self.subTest(times=times), self.assertRaises(ValueError):
                w.cmd_scroll({"element": "e1", "times": times})


class RestartTest(unittest.TestCase):
    def test_calls_before_start_fail_then_restart_works(self):
        profile = tempfile.mkdtemp(prefix="bok-test-")
        b = Browser(profile_dir=profile, headless=True)
        try:
            self.assertFalse(b.alive)
            self.assertEqual(b.open(fixture("second_page.html"))["title"], "Lịch sử")  # auto-start
            self.assertTrue(b.alive)
            b.close()
            self.assertFalse(b.alive)
            with self.assertRaises(BrowserError) as cm:  # N8: no silent relaunch after an explicit close()
                b.open(fixture("upload_form.html"))
            self.assertIn("trình duyệt đã đóng", str(cm.exception))
            self.assertFalse(b.alive)
            with self.assertRaises(BrowserError):
                b.snapshot()
            b.start()  # explicit start reopens
            self.assertEqual(b.open(fixture("upload_form.html"))["title"], "Đăng video")
            b.proc.kill()  # worker dies: the next call restarts it by itself (page state is lost)
            b.proc.wait()
            self.assertFalse(b.alive)
            self.assertEqual(b.open(fixture("second_page.html"))["title"], "Lịch sử")
            self.assertTrue(b.alive)
        finally:
            b.close()
            shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
