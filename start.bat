@echo off
rem AI Website Builder - Windows: create the venv if missing, install, run on http://127.0.0.1:5050
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is needed ^(the pinned packages require it^).
  exit /b 1
)
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
fc /b requirements.txt .venv\.requirements.stamp >nul 2>nul
if errorlevel 1 (
  python -m pip install -r requirements.txt || exit /b 1
  copy /y requirements.txt .venv\.requirements.stamp >nul
)
if not exist .env copy .env.example .env >nul
python app.py
