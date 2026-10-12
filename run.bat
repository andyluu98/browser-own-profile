@echo off
rem Launcher used by the plugin skill: keeps the Python env, Chrome profile, output and logs in a fixed
rem folder (%LOCALAPPDATA%\browser-own-profile) so plugin updates never lose them.
setlocal
set "ROOT=%~dp0"
set "BOK_HOME=%LOCALAPPDATA%\browser-own-profile"
set "PY_ENV=%BOK_HOME%\venv\Scripts\python.exe"
if not exist "%BOK_HOME%" mkdir "%BOK_HOME%"

if not exist "%PY_ENV%" (
  set "PYCMD="
  where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PYCMD=py -3"
  if not defined PYCMD (
    where python >nul 2>nul && python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PYCMD=python"
  )
)
if not exist "%PY_ENV%" if not defined PYCMD (
  echo CHUA CO PYTHON 3.11+: cai tai https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) roi chay lai.
  exit /b 1
)
if not exist "%PY_ENV%" (
  echo Dang tao moi truong Python lan dau...
  %PYCMD% -m venv "%BOK_HOME%\venv" || exit /b 1
)

rem Reinstall libraries when requirements.txt changed (first run included).
fc /b "%ROOT%requirements.txt" "%BOK_HOME%\requirements.installed.txt" >nul 2>nul
if errorlevel 1 (
  "%PY_ENV%" -m pip install --disable-pip-version-check -q -r "%ROOT%requirements.txt" || exit /b 1
  copy /y "%ROOT%requirements.txt" "%BOK_HOME%\requirements.installed.txt" >nul
)

cd /d "%BOK_HOME%"
set "PYTHONPATH=%ROOT%"
set "PYTHONIOENCODING=utf-8"
"%PY_ENV%" -m browser_kit %*
