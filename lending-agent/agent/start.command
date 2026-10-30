#!/bin/bash
# Mac / Linux: double-click (Mac) or run ./start.command. First run installs everything
# and asks for your Claude API key, which is saved in .env next to this file.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python is not installed. Install Python 3.12 from https://www.python.org/downloads/"
  read -r -p "Press Enter to close." _; exit 1
fi
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
echo "Checking components (first run takes a minute)..."
pip install -q --disable-pip-version-check -r requirements.txt || { read -r -p "Install failed. Press Enter."; exit 1; }
if [ ! -f .env ]; then
  read -r -s -p "Paste your Claude API key (starts with sk-ant-) and press Enter: " KEY; echo
  umask 077; printf 'ANTHROPIC_API_KEY=%s\n' "$KEY" > .env
fi
set -a; source .env; set +a
echo "Starting LendAgent. Your browser will open at http://localhost:8501 (close this window to stop)."
streamlit run broker_app.py --browser.gatherUsageStats false
