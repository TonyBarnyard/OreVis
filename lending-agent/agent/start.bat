@echo off
rem Windows: double-click. First run installs everything and asks for your Claude API key,
rem which is saved in .env next to this file.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
where python >nul 2>nul || (
  echo Python is not installed. Install Python 3.12 from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during install.
  pause & exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
echo Checking components (first run takes a minute)...
pip install -q --disable-pip-version-check -r requirements.txt || (echo Install failed. & pause & exit /b 1)
if not exist .env (
  set /p KEY=Paste your Claude API key ^(starts with sk-ant-^) and press Enter: 
  > .env echo ANTHROPIC_API_KEY=!KEY!
)
for /f "usebackq tokens=1,* delims==" %%a in (".env") do set "%%a=%%b"
echo Starting LendAgent. Your browser will open at http://localhost:8501 (close this window to stop).
streamlit run broker_app.py --browser.gatherUsageStats false
