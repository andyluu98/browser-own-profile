#!/bin/bash
# Cài đặt browser-own-profile trên macOS: bấm đúp file này trong Finder.
cd "$(dirname "$0")" || exit 1
echo "============================================"
echo "  Cài đặt browser-own-profile (macOS)"
echo "============================================"

PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Máy chưa có Python 3.11 trở lên. Tải tại https://www.python.org/downloads/macos/ , cài xong chạy lại file này."
  read -r -p "Nhấn Enter để đóng..."
  exit 1
fi
if [ ! -d "/Applications/Google Chrome.app" ] && [ ! -d "$HOME/Applications/Google Chrome.app" ]; then
  echo "Chưa thấy Google Chrome. Tải tại https://www.google.com/chrome/ rồi chạy lại."
fi

echo "[1/3] Tạo môi trường .venv bằng $PY ..."
[ -x .venv/bin/python ] || "$PY" -m venv .venv || { echo "Không tạo được .venv"; exit 1; }
echo "[2/3] Cài thư viện ..."
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
echo "[3/3] Kiểm tra ..."
.venv/bin/python -m browser_kit doctor
echo
echo "Xong. Mở Claude Code trong thư mục này rồi nói việc cần làm."
read -r -p "Nhấn Enter để đóng..."
