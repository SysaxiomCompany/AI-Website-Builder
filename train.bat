@echo off
rem Retrain and evaluate the two classifiers (Windows): venv + install + train + evaluate.
rem Needs the team's ML-Training-App folder (default ..\ML-Training-App, or set ML_TRAINING_APP).
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
python ml\train.py || exit /b 1
python ml\evaluate.py || exit /b 1
echo Done. New files are in ml\artifacts\ and the plot is docs\test-evidence\ml-evaluation.png
