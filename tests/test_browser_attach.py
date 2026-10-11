"""Attach mode (the user's own Chrome): endpoint discovery and a clear error when not enabled. No Chrome needed."""

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from browser_kit import worker as browser_worker  # noqa: E402
from browser_kit.client import Browser, BrowserError  # noqa: E402


class EndpointTests(unittest.TestCase):
    def test_reads_port_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "DevToolsActivePort").write_text("9222\n/devtools/browser/abc-123\n", encoding="utf-8")
            self.assertEqual(browser_worker.attach_endpoint(tmp), "ws://127.0.0.1:9222/devtools/browser/abc-123")

    def test_missing_file_explains_how_to_enable(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError) as ctx:
                browser_worker.attach_endpoint(tmp)
        self.assertIn("chrome://inspect/#remote-debugging", str(ctx.exception))

    def test_garbage_port_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "DevToolsActivePort").write_text("abc\n/x\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                browser_worker.attach_endpoint(tmp)

    def test_client_reports_the_worker_error(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"BOK_CHROME_USER_DATA": tmp}):
            b = Browser(attach=True)
            with self.assertRaises(BrowserError) as ctx:
                b.start()
        # Without a browser engine installed the worker reports that first; otherwise the attach hint.
        self.assertTrue("remote debugging" in str(ctx.exception) or "công cụ điều khiển" in str(ctx.exception))
        self.assertFalse(b.alive)


if __name__ == "__main__":
    unittest.main()
