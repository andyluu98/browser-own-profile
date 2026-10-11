"""Browser worker. Drives Chrome through browser-harness (raw CDP via its daemon) in its own process so a
crash in the low-level libraries cannot take down the listening loop. Protocol: one JSON line per command
on stdin {"id", "cmd", ...}; one JSON line reply {"id", "ok": true, ...} or {"id", "ok": false, "error"}.
Prints {"ready": true, "version": ...} once Chrome is up.

Run: python -m browser_kit.worker --profile <dir> [--headless]
     python -m browser_kit.worker --attach   (the user's own running Chrome, see attach_endpoint)
Only snapshot.js and the fixed snippets below are ever evaluated in a page: no caller-supplied JS.
"""

import argparse
import ctypes
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.request
from urllib.parse import urlparse

SNAPSHOT_JS = pathlib.Path(__file__).with_name("snapshot.js")
COMMAND_TIMEOUT_S = 30
ACTION_TIMEOUT_S = 5
LAUNCH_TIMEOUT_S = 25
APPROVAL_WAIT_S = 50  # the user clicks Allow in Chrome; the client gives up at 60 s
KEYS = {"Enter": (13, "\r"), "Tab": (9, ""), "Escape": (27, "")}
READ_LIMIT = 8000
MAX_SCROLLS = 5
SCROLL_PX = 600
SCROLL_PAUSE_S = 1.5  # time for the page to load the next batch
CTRL, CMD = 2, 4  # CDP modifier bits
# Fixed snippets (no caller-supplied JS). Element ids are validated as e<digits> before use.
NAME_JS = "el => (typeof window.__bokName === 'function' ? window.__bokName(el) : null)"
TEXT_JS = "el => (typeof window.__bokText === 'function' ? window.__bokText(el) : null)"
# Scroll into view, then return the click point if the element is enabled, visible and not covered.
POINT_JS = """el => {
  if (!el || !el.isConnected) return {err: 'gone'};
  el.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
  if (el.matches(':disabled') || el.closest('[aria-disabled="true"],[inert]')) return {err: 'disabled'};
  const r = el.getBoundingClientRect();
  if (!r.width || !r.height || !el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}))
    return {err: 'hidden'};
  const x = r.x + r.width / 2, y = r.y + r.height / 2;
  if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) return {err: 'hidden'};
  const hit = el.getRootNode().elementFromPoint(x, y);
  if (!hit || !el.contains(hit)) return {err: 'covered'};
  return {x, y};
}"""
# Focus and select the current content of a native editable field; false when it is not one.
SELECT_JS = """el => {
  const tag = el.tagName, type = (el.getAttribute('type') || 'text').toLowerCase();
  const input = tag === 'INPUT' && !['checkbox', 'radio', 'file', 'button', 'submit', 'reset', 'image',
                                     'hidden', 'range', 'color'].includes(type);
  if (el.matches(':disabled') || el.readOnly) return false;
  el.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
  if (input || tag === 'TEXTAREA') { el.focus(); el.select(); return true; }
  if (el.isContentEditable) {
    el.focus();
    const sel = getSelection(); sel.removeAllRanges();
    const range = document.createRange(); range.selectNodeContents(el); sel.addRange(range);
    return true;
  }
  return false;
}"""
NOT_ACTIONABLE = {
    "gone": "không thấy phần tử (trang đã đổi, cần chụp lại)",
    "disabled": "phần tử đang bị khóa, chưa bấm được",
    "hidden": "phần tử đang bị ẩn, chưa bấm được",
    "covered": "phần tử đang bị thứ khác che, chưa bấm được",
}
CLOSED_MARKERS = ("targetclosed", "has been closed", "target closed", "browser closed", "connection closed",
                  "no target with given id", "session with given id not found", "not attached to an active page",
                  "connectionrefused", "connection refused")
RETRY_AFTER_RELAUNCH = {"open", "snapshot"}
CLOSED_MSG = "trang đã bị đóng, hãy mở lại trang"
NO_ENGINE_MSG = ("chưa có công cụ điều khiển trình duyệt (cần browser-harness); các bước trên web chưa làm "
                 "được")
IS_MAC = sys.platform == "darwin"
CHROME_PATHS = (
    pathlib.Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Google", "Chrome", "Application",
                 "chrome.exe"),
    pathlib.Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Google", "Chrome",
                 "Application", "chrome.exe"),
    pathlib.Path(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    pathlib.Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def is_closed_error(exc):
    text = f"{type(exc).__name__} {exc}".lower()
    return any(m in text for m in CLOSED_MARKERS)


def fold(s):
    return " ".join(unicodedata.normalize("NFC", s).split()).casefold()


def app_data():
    """Per-user app data folder: %LOCALAPPDATA% on Windows, ~/Library/Application Support on macOS."""
    if IS_MAC:
        return pathlib.Path.home() / "Library" / "Application Support"
    return pathlib.Path(os.environ.get("LOCALAPPDATA") or pathlib.Path.home())


def default_chrome_data():
    if IS_MAC:
        return str(app_data() / "Google" / "Chrome")
    return str(app_data() / "Google" / "Chrome" / "User Data")


def attach_endpoint(user_data=None):
    """ws:// endpoint of the user's own Chrome. Chrome writes DevToolsActivePort (port, path) into its user
    data folder once the user turns on chrome://inspect/#remote-debugging; Chrome then asks the user to
    allow each connection. Nothing here bypasses that prompt."""
    base = user_data or os.environ.get("BOK_CHROME_USER_DATA") or default_chrome_data()
    port_file = pathlib.Path(base) / "DevToolsActivePort"
    try:
        port, path = port_file.read_text(encoding="utf-8").splitlines()[:2]
    except (OSError, ValueError):
        raise RuntimeError("Chrome chưa bật remote debugging: mở chrome://inspect/#remote-debugging, bật cho "
                           "phép, rồi chạy lại") from None
    return f"ws://127.0.0.1:{int(port)}{path.strip()}"


def default_profile():
    if os.environ.get("BOK_PROFILE"):  # another profile folder, e.g. one already logged in
        return pathlib.Path(os.environ["BOK_PROFILE"])
    return app_data() / "browser-own-profile" / "chrome"


def find_chrome():
    for p in CHROME_PATHS:
        if p.is_file():
            return str(p)
    found = shutil.which("chrome") or shutil.which("google-chrome")
    if found:
        return found
    raise RuntimeError("không tìm thấy Google Chrome trên máy")


def kill_children_with_me():
    """Windows: put this process in a kill-on-close job, so Chrome and the harness daemon we start die with
    the worker even when the client terminates it."""
    if os.name != "nt":
        return
    k32 = ctypes.windll.kernel32

    class Basic(ctypes.Structure):
        _fields_ = [("a", ctypes.c_int64), ("b", ctypes.c_int64), ("LimitFlags", ctypes.c_uint32),
                    ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", ctypes.c_uint32), ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", ctypes.c_uint32), ("SchedulingClass", ctypes.c_uint32)]

    class Extended(ctypes.Structure):
        _fields_ = [("Basic", Basic), ("Io", ctypes.c_uint64 * 6), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32.CreateJobObjectW.restype = ctypes.c_void_p
    job = k32.CreateJobObjectW(None, None)
    if not job:
        return
    info = Extended()
    info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    k32.SetInformationJobObject(ctypes.c_void_p(job), 9, ctypes.byref(info), ctypes.sizeof(info))
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.AssignProcessToJobObject(ctypes.c_void_p(job), ctypes.c_void_p(k32.GetCurrentProcess()))
    # The handle is intentionally kept open for the life of the process.


class Worker:
    def __init__(self, profile, headless, attach=False):
        # Set before importing browser_harness: it reads these at import time and passes them to its daemon.
        os.environ["BH_TELEMETRY"] = "0"  # no usage data to Browser Use
        os.environ["BH_TAB_MARKER"] = "0"  # never rewrite page titles
        os.environ.pop("BROWSER_USE_API_KEY", None)  # local only, never their cloud
        # A named daemon opens its own blank tab instead of attaching to the user's first tab.
        self.name = "bok-main" if attach else f"bok-{os.getpid()}"
        os.environ["BU_NAME"] = self.name
        try:
            from browser_harness import admin, helpers
        except ImportError:
            raise RuntimeError(NO_ENGINE_MSG) from None
        self.admin, self.h = admin, helpers
        self.headless = headless
        self.profile = profile
        # attach: drive the user's own Chrome, but only tabs this worker opened (self.own); never read,
        # switch to or close the user's other tabs, never close their browser.
        self.attach = attach
        self.own = []  # target ids of our tabs, oldest first
        self.sessions = {}  # target id -> CDP session id
        self.page = None  # current target id
        self.chrome = None  # Chrome process we launched (not in attach mode)
        self.snapshot_js = SNAPSHOT_JS.read_text(encoding="utf-8")
        kill_children_with_me()
        self._launch()

    # lifecycle

    def _launch(self):
        self.own, self.sessions, self.page = [], {}, None
        if self.attach:
            attach_endpoint()  # clear message when remote debugging is off; the harness would open tabs
            custom = os.environ.get("BOK_CHROME_USER_DATA")
            env = {"BU_CDP_WS": attach_endpoint()} if custom and os.path.normcase(custom) != os.path.normcase(
                default_chrome_data()) else None
            if env:
                os.environ.update(env)
            else:  # Chrome's default profile: the harness finds it and waits for the user's Allow
                os.environ.pop("BU_CDP_WS", None)
                os.environ.pop("BU_CDP_URL", None)
            self.admin.ensure_daemon(wait=APPROVAL_WAIT_S, name=self.name, env=env)
        else:
            ws = self._start_chrome()
            os.environ["BU_CDP_WS"] = ws
            self.admin.ensure_daemon(wait=LAUNCH_TIMEOUT_S, name=self.name, env={"BU_CDP_WS": ws})
        self.version = self.cdp("Browser.getVersion").get("product")
        try:  # the daemon's own blank tab becomes our first tab (no extra tab in the user's window)
            tab = self.h.current_tab()
            if tab["url"] in ("", "about:blank"):
                self._adopt(tab["targetId"])
        except Exception:
            pass

    def _start_chrome(self):
        profile = pathlib.Path(self.profile)
        port_file = profile / "DevToolsActivePort"
        try:
            before = port_file.stat().st_mtime
        except OSError:
            before = None
        args = [find_chrome(), f"--user-data-dir={profile}", "--remote-debugging-port=0", "--no-first-run",
                "--no-default-browser-check"]
        if self.headless:
            args += ["--headless=new", "--window-size=1280,800"]
        args.append("about:blank")
        self.chrome = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + LAUNCH_TIMEOUT_S
        while time.monotonic() < deadline:
            if self.chrome.poll() is not None:
                raise RuntimeError("Chrome hồ sơ tự động đã mở sẵn hoặc không chạy được: đóng nó rồi thử lại")
            try:
                if before is None or port_file.stat().st_mtime != before:
                    port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                        return json.loads(r.read())["webSocketDebuggerUrl"]
            except (OSError, ValueError, KeyError, IndexError):
                pass
            time.sleep(0.2)
        raise RuntimeError("Chrome không mở cổng điều khiển kịp")

    def relaunch(self):
        """Chrome or the connection was closed (user closed the window, crash): start again.
        In attach mode only reconnect: the user's browser is never closed or relaunched by us."""
        self._stop()
        self._launch()

    def _stop(self):
        try:
            self.admin.restart_daemon(self.name)  # despite the name: only stops it
        except Exception:
            pass
        if self.chrome is not None:
            if self.chrome.poll() is None:
                self.chrome.kill()
            try:
                self.chrome.wait(10)
            except subprocess.TimeoutExpired:
                pass
            self.chrome = None

    def broken(self):
        if self.chrome is not None and self.chrome.poll() is not None:
            return True
        try:
            self.cdp("Target.getTargets")
            return False
        except Exception:
            return True

    # CDP plumbing

    def cdp(self, method, session=None, timeout=ACTION_TIMEOUT_S, **params):
        return self.h.cdp(method, session_id=session, _response_timeout=timeout, **params)

    def targets(self):
        return {t["targetId"]: t for t in self.cdp("Target.getTargets")["targetInfos"] if t["type"] == "page"}

    def _adopt(self, tid):
        self.sessions[tid] = self.cdp("Target.attachToTarget", targetId=tid, flatten=True)["sessionId"]
        self.own.append(tid)
        self.page = tid
        try:
            self.cdp("Target.activateTarget", targetId=tid)
        except Exception:
            pass
        # Keep rendering (and so input events) going even when the tab or window is not in front.
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)

    def call(self, method, timeout=ACTION_TIMEOUT_S, **params):
        return self.cdp(method, session=self.sessions[self.page], timeout=timeout, **params)

    def evaluate(self, expression, timeout=ACTION_TIMEOUT_S, by_value=True):
        r = self.call("Runtime.evaluate", timeout=timeout, expression=expression, returnByValue=by_value,
                      awaitPromise=False)
        if r.get("exceptionDetails"):
            d = r["exceptionDetails"]
            raise ValueError((d.get("exception") or {}).get("description") or d.get("text") or "lỗi chạy trang")
        return r.get("result", {}) if not by_value else r.get("result", {}).get("value")

    def wait_ready(self, timeout):
        """Until the document is past 'loading' (Playwright's domcontentloaded); errors while navigating."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                if self.evaluate("document.readyState") in ("interactive", "complete"):
                    return True
            except Exception as e:
                if is_closed_error(e):
                    raise
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def active(self):
        alive = self.targets()
        self.own = [t for t in self.own if t in alive]
        for tid in list(self.sessions):
            if tid not in alive:
                del self.sessions[tid]
        if self.page not in alive:
            if self.own:
                self.page = self.own[-1]
            else:  # a new tab of our own
                self._adopt(self.cdp("Target.createTarget", url="about:blank")["targetId"])
        return self.page

    def follow_new_page(self, known):
        """Switch to a tab/popup our page opened during the last action (never one the user opened)."""
        opener = self.page
        fresh = [t for tid, t in self.targets().items() if tid not in known and t.get("openerId") == opener]
        for t in reversed(fresh):
            if self._settled(t["targetId"]):
                self._adopt(t["targetId"])
                self.wait_ready(ACTION_TIMEOUT_S)
                break
        return self.active()

    def _settled(self, tid):
        """False for pages that stay about:blank for 1 s or that close right away (ad/tracker pop-unders)."""
        deadline = time.monotonic() + 1
        while True:
            t = self.targets().get(tid)
            if t is None:
                return False
            if t.get("url") not in ("", "about:blank"):
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def info(self):
        self.active()
        try:
            return self.evaluate("({url: location.href, title: document.title})")
        except Exception:
            t = self.targets().get(self.page, {})
            return {"url": t.get("url", ""), "title": t.get("title", "")}

    @staticmethod
    def selector(req):
        element = req.get("element")
        if not isinstance(element, str) or not element.startswith("e") or not element[1:].isdigit():
            raise ValueError("mã phần tử không hợp lệ")
        return f"document.querySelector('[data-bok-id=\"{element}\"]')"

    def on_element(self, req, fn_js):
        """Run a fixed snippet on the snapshot element named in req; error if it is gone."""
        sel = self.selector(req)
        self.active()
        if not self.evaluate(f"!!{sel}"):
            raise ValueError(f"không thấy phần tử {req['element']} (trang đã đổi, cần chụp lại)")
        return self.evaluate(f"({fn_js})({sel})")

    def mouse_click(self, x, y):
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left",
                      clickCount=0 if kind == "mouseMoved" else 1)

    def click_element(self, req):
        """Wait (bounded) until the element can be clicked like a person would, then click its centre."""
        deadline = time.monotonic() + ACTION_TIMEOUT_S
        while True:
            point = self.on_element(req, POINT_JS)
            if "x" in point:
                self.mouse_click(point["x"], point["y"])
                return
            if point["err"] == "gone" or time.monotonic() >= deadline:
                raise ValueError(NOT_ACTIONABLE[point["err"]])
            time.sleep(0.1)

    def key(self, key, code=None, vk=0, text="", modifiers=0, commands=None):
        down = {"type": "keyDown" if text else "rawKeyDown", "key": key, "code": code or key,
                "windowsVirtualKeyCode": vk, "modifiers": modifiers}
        if text:
            down["text"] = text
        if commands:
            down["commands"] = commands
        self.call("Input.dispatchKeyEvent", **down)
        self.call("Input.dispatchKeyEvent", type="keyUp", key=key, code=code or key, windowsVirtualKeyCode=vk,
                  modifiers=modifiers)

    # commands

    def cmd_open(self, req):
        url = req.get("url")
        if not isinstance(url, str):
            raise ValueError("thiếu url")
        scheme = urlparse(url).scheme.lower()
        if not (scheme == "https" or (scheme == "file" and self.headless)):
            raise ValueError("chỉ mở được địa chỉ https://")
        self.active()
        r = self.call("Page.navigate", timeout=COMMAND_TIMEOUT_S, url=url)
        if r.get("errorText"):
            raise ValueError(f"không mở được trang ({r['errorText']})")
        self.wait_ready(COMMAND_TIMEOUT_S)
        return self.info()

    def cmd_snapshot(self, req):
        self.active()
        self.wait_ready(5)
        return self.evaluate(f"({self.snapshot_js})()", timeout=COMMAND_TIMEOUT_S)

    def cmd_click(self, req):
        expect = req.get("expect_name")
        if expect is not None and not isinstance(expect, str):
            raise ValueError("expect_name phải là chuỗi")
        expect_text = req.get("expect_text")
        if expect_text is not None and not isinstance(expect_text, str):
            raise ValueError("expect_text phải là chuỗi")
        self.selector(req)
        if expect is not None:
            current = self.on_element(req, NAME_JS)
            if current is None:
                raise ValueError("không đọc được tên phần tử (trang đã đổi, cần chụp lại)")
            if fold(current) != fold(expect):
                raise ValueError(f"phần tử đã đổi: '{expect}' -> '{current}'")
        if expect_text:  # only when the element had visible text in the snapshot
            now = self.on_element(req, TEXT_JS)
            if now is None:
                raise ValueError("không đọc được chữ của phần tử (trang đã đổi, cần chụp lại)")
            if fold(now) != fold(expect_text):
                raise ValueError(f"chữ của phần tử đã đổi: '{expect_text}' -> '{now}'")
        known = set(self.targets())
        self.click_element(req)
        time.sleep(0.4)  # let popups / navigation start
        self.follow_new_page(known)
        self.wait_ready(ACTION_TIMEOUT_S)
        return self.info()

    def cmd_fill(self, req):
        text = req.get("text")
        if not isinstance(text, str):
            raise ValueError("thiếu text")
        if not self.on_element(req, SELECT_JS):
            # role=textbox on a non-editable host (custom widgets): click, select all, type.
            self.click_element(req)
            self.key("a", code="KeyA", vk=65, modifiers=CMD if IS_MAC else CTRL,
                     commands=["selectAll"])
        if text:
            self.call("Input.insertText", text=text)  # replaces the selection
        else:
            self.key("Delete", vk=46)
        return {}

    def cmd_upload(self, req):
        path = req.get("path")
        if not isinstance(path, str) or not os.path.isfile(path):
            raise ValueError("không thấy file để tải lên")
        sel = self.selector(req)
        self.active()
        obj = self.evaluate(f"(el => el && el.tagName === 'INPUT' && el.type === 'file' ? el : null)({sel})",
                            by_value=False)
        if not obj.get("objectId"):
            raise ValueError(f"phần tử {req['element']} không phải ô chọn file (trang đã đổi, cần chụp lại)")
        self.call("DOM.setFileInputFiles", files=[os.path.abspath(path)], objectId=obj["objectId"])
        return {}

    def cmd_press(self, req):
        key = req.get("key")
        if key not in KEYS:
            raise ValueError("phím không hỗ trợ (chỉ Enter, Tab, Escape)")
        self.active()
        known = set(self.targets())
        vk, text = KEYS[key]
        self.key(key, vk=vk, text=text)
        time.sleep(0.3)
        self.follow_new_page(known)
        return self.info()

    def cmd_scroll(self, req):
        """Mouse-wheel over a snapshot element (scrolls the list it sits in), 1 to MAX_SCROLLS notches,
        pausing so the page can load more."""
        times = req.get("times", 1)
        if not isinstance(times, int) or not 1 <= times <= MAX_SCROLLS:
            raise ValueError(f"số lần cuộn phải từ 1 đến {MAX_SCROLLS}")
        point = self.on_element(req, POINT_JS)
        if "x" not in point and point["err"] != "covered":
            raise ValueError(NOT_ACTIONABLE[point["err"]])
        if "x" not in point:  # covered elements still sit in the list; wheel over their centre
            point = self.on_element(req, "el => { const r = el.getBoundingClientRect(); "
                                         "return {x: r.x + r.width / 2, y: r.y + r.height / 2}; }")
        for _ in range(times):
            self.call("Input.dispatchMouseEvent", type="mouseWheel", x=point["x"], y=point["y"], deltaX=0,
                      deltaY=SCROLL_PX)
            time.sleep(SCROLL_PAUSE_S)
        return {}

    def cmd_read_text(self, req):
        self.active()
        text = self.evaluate("document.body ? document.body.innerText : ''")
        return {"text": text.strip()[:READ_LIMIT]}

    def cmd_debug_close_pages(self, req):
        """Tests only (serve() accepts it with --headless only): closes the whole browser."""
        if not self.headless:
            raise ValueError("lệnh không hỗ trợ: debug_close_pages")
        try:
            self.cdp("Browser.close")
        except Exception:
            pass
        if self.chrome is not None:
            try:
                self.chrome.wait(10)
            except subprocess.TimeoutExpired:
                self.chrome.kill()
        return {}

    def run(self, cmd, req):
        """Run a command; if Chrome or the connection was closed, relaunch once and retry (open, snapshot)
        or report."""
        fn = getattr(self, "cmd_" + cmd)
        if cmd != "debug_close_pages" and self.broken():
            self.relaunch()
            if cmd not in RETRY_AFTER_RELAUNCH:
                raise ValueError(CLOSED_MSG)
        try:
            return fn(req)
        except Exception as e:
            if cmd == "debug_close_pages" or not is_closed_error(e):
                raise
            self.relaunch()
            if cmd in RETRY_AFTER_RELAUNCH:
                return fn(req)
            raise ValueError(CLOSED_MSG)

    def close(self):
        try:
            if self.attach:
                for tid in self.own:  # only our tabs; the user's browser stays open
                    try:
                        self.cdp("Target.closeTarget", targetId=tid)
                    except Exception:
                        pass
            else:
                try:
                    self.cdp("Browser.close")
                except Exception:
                    pass
        finally:
            self._stop()


def serve(worker):
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            cmd = req.get("cmd")
            if cmd == "close":
                print(json.dumps({"id": rid, "ok": True}), flush=True)
                return
            allowed = {"open", "snapshot", "click", "fill", "upload", "press", "scroll", "read_text"}
            if worker.headless:
                allowed.add("debug_close_pages")
            if cmd not in allowed:
                raise ValueError(f"lệnh không hỗ trợ: {cmd}")
            reply = {"id": rid, "ok": True, **worker.run(cmd, req)}
        except Exception as e:  # report and keep serving
            reply = {"id": rid, "ok": False, "error": f"{type(e).__name__}: {e}".splitlines()[0][:300]}
        print(json.dumps(reply, ensure_ascii=False), flush=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None)
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--attach", action="store_true", help="use the user's own running Chrome")
    args = ap.parse_args()
    profile = pathlib.Path(args.profile) if args.profile else default_profile()
    if not args.attach:
        profile.mkdir(parents=True, exist_ok=True)
    try:
        worker = Worker(profile, args.headless and not args.attach, attach=args.attach)
    except Exception as e:
        print(json.dumps({"ready": False, "error": str(e).splitlines()[0][:300]}, ensure_ascii=False), flush=True)
        return
    print(json.dumps({"ready": True, "version": worker.version}), flush=True)
    try:
        serve(worker)
    finally:
        try:
            worker.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
