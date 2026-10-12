#!/bin/bash
# Launcher used by the plugin skill on macOS: Python env, Chrome profile, output and logs live in
# ~/Library/Application Support/browser-own-profile so plugin updates never lose them.
ROOT="$(cd "$(dirname "$0")" && pwd)"
BOK_HOME="$HOME/Library/Application Support/browser-own-profile"
PY_ENV="$BOK_HOME/venv/bin/python"
mkdir -p "$BOK_HOME"
if [ ! -x "$PY_ENV" ]; then
  PYCMD=""
  for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
      PYCMD="$c"; break
    fi
  done
  [ -n "$PYCMD" ] || { echo "CHƯA CÓ PYTHON 3.11+: cài tại https://www.python.org/downloads/macos/ rồi chạy lại."; exit 1; }
  echo "Đang tạo môi trường Python lần đầu..."
  "$PYCMD" -m venv "$BOK_HOME/venv" || exit 1
fi
if ! cmp -s "$ROOT/requirements.txt" "$BOK_HOME/requirements.installed.txt"; then
  "$PY_ENV" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements.txt" || exit 1
  cp "$ROOT/requirements.txt" "$BOK_HOME/requirements.installed.txt"
fi
cd "$BOK_HOME" || exit 1
PYTHONPATH="$ROOT" exec "$PY_ENV" -m browser_kit "$@"
