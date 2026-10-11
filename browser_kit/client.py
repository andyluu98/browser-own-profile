"""Client for worker.py (browser-harness in a separate process, JSON lines over stdin/stdout).

The model never sees selectors or JS: it only picks an element id from snapshot() and the worker acts
on that id. open() takes https:// only (file:// also when headless, for tests).
"""

import itertools
import os
import json
import pathlib
import queue
import subprocess
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
STARTUP_TIMEOUT = 60
CALL_TIMEOUT = 35


class BrowserError(RuntimeError):
    pass


class Browser:
    def __init__(self, profile_dir=None, headless=False, python=sys.executable, attach=False):
        self.profile_dir = str(profile_dir) if profile_dir else None
        self.headless = headless
        self.attach = attach  # True: the user's own Chrome (remote debugging allowed by the user)
        self.python = python
        self.proc = None
        self.lines = None
        self.version = None
        self.closed = False  # set by an explicit close(); only start() reopens
        self._ids = itertools.count(1)
        self._lock = threading.RLock()

    # lifecycle

    @property
    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        with self._lock:
            self.closed = False
            if self.alive:
                return
            self._kill()
            cmd = [self.python, "-m", "browser_kit.worker"]
            if self.profile_dir:
                cmd += ["--profile", self.profile_dir]
            if self.headless:
                cmd.append("--headless")
            if self.attach:
                cmd.append("--attach")
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            self.proc = subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, env=env, encoding="utf-8", bufsize=1)
            self.lines = queue.Queue()
            threading.Thread(target=self._pump, args=(self.proc, self.lines), daemon=True).start()
            try:
                ready = self._read(STARTUP_TIMEOUT)
            except BrowserError:
                self._kill()
                raise BrowserError("Trình duyệt không khởi động được")
            if not ready.get("ready"):
                self._kill()
                raise BrowserError(ready.get("error") or "Trình duyệt không khởi động được")
            self.version = ready.get("version")

    @staticmethod
    def _pump(proc, lines):
        try:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("{"):
                    lines.put(line)
        except (OSError, ValueError):
            pass
        lines.put(None)  # worker gone

    def _read(self, timeout):
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            raise BrowserError("Trình duyệt không trả lời kịp")
        if line is None:
            raise BrowserError("Trình duyệt đã tắt")
        try:
            return json.loads(line)
        except ValueError:
            raise BrowserError("Trình duyệt trả dữ liệu lỗi")

    def _kill(self):
        proc, self.proc = self.proc, None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if proc is not None:
            for pipe in (proc.stdin, proc.stdout):
                try:
                    pipe.close()
                except (OSError, ValueError):
                    pass

    # commands

    def _call(self, cmd, timeout=CALL_TIMEOUT, **args):
        with self._lock:
            if self.closed:
                raise BrowserError("trình duyệt đã đóng")
            if not self.alive:
                self.start()  # worker died or was killed after a timeout: restart once (page state is lost)
            rid = next(self._ids)
            try:
                self.proc.stdin.write(json.dumps({"id": rid, "cmd": cmd, **args}, ensure_ascii=False) + "\n")
                self.proc.stdin.flush()
                while True:  # skip stale replies from an earlier timed-out call
                    reply = self._read(timeout)
                    if reply.get("id") == rid:
                        break
            except (OSError, ValueError):
                self._kill()
                raise BrowserError("Trình duyệt đã tắt")
            except BrowserError:
                self._kill()  # dead or stuck: next start() gives a clean worker
                raise
            if not reply.get("ok"):
                raise BrowserError(reply.get("error", "lỗi không rõ"))
            reply.pop("id", None)
            return reply

    def open(self, url):
        r = self._call("open", url=url)
        return {"url": r["url"], "title": r["title"]}

    def snapshot(self):
        r = self._call("snapshot")
        r.pop("ok", None)
        return r

    def click(self, element_id, expect_name=None, expect_text=None):
        """expect_name / expect_text: name and visible text seen in the snapshot; the click is refused if
        either changed (an empty expect_text is not compared)."""
        args = {"element": element_id}
        if expect_name is not None:
            args["expect_name"] = expect_name
        if expect_text is not None:
            args["expect_text"] = expect_text
        return self._call("click", **args)

    def fill(self, element_id, text):
        return self._call("fill", element=element_id, text=text)

    def upload(self, element_id, path):
        return self._call("upload", element=element_id, path=str(path))

    def press(self, key):
        return self._call("press", key=key)

    def scroll(self, element_id, times=1):
        return self._call("scroll", element=element_id, times=times)

    def read_text(self):
        return self._call("read_text")["text"]

    def close(self):
        with self._lock:
            if self.alive:
                try:
                    self.closed = False  # allow the close command itself through
                    self._call("close", timeout=10)
                except BrowserError:
                    pass
                try:
                    self.proc.wait(10)
                except (subprocess.TimeoutExpired, AttributeError):
                    pass
            self._kill()
            self.closed = True
