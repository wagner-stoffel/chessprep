@echo off
cd /d "%~dp0"
set "PIP_CACHE_DIR=%CD%\.pip-cache"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv || (echo Python 3.11+ is required. & pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Failed to install dependencies. & pause & exit /b 1)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
