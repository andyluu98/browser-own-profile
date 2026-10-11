@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Cai dat browser-own-profile (Windows)
echo ============================================
echo.

set "PY="
set "CHECK=import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "%CHECK%" >nul 2>nul
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "%CHECK%" >nul 2>nul
    if not errorlevel 1 set "PY=python"
  )
)
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""

if not defined PY (
  echo May chua co Python 3.11 tro len.
  choice /c YN /m "Cai Python 3.12 tu dong bang winget (Y = co, N = khong)"
  if errorlevel 2 (
    echo Hay tai Python tai https://www.python.org/downloads/ , khi cai nho tick "Add python.exe to PATH", roi chay lai file nay.
    pause
    exit /b 1
  )
  winget install -e --id Python.Python.3.12 --scope user
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
)
if not defined PY (
  echo Chua cai duoc Python. Hay cai tay tai https://www.python.org/downloads/ roi chay lai file nay.
  pause
  exit /b 1
)

echo [1/3] Tao moi truong .venv bang %PY% ...
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Khong tao duoc .venv.
  pause
  exit /b 1
)
echo [2/3] Cai thu vien ...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
echo [3/3] Kiem tra ...
".venv\Scripts\python.exe" -m browser_kit doctor
echo.
echo Xong. Mo Claude Code trong thu muc nay roi noi viec can lam, vi du:
echo   "Tim 10 ban phim ban chay tam 1 trieu tren Shopee"
pause
