@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo Run these first:
  echo   python -m venv .venv
  echo   .venv\Scripts\pip install -r requirements.txt
  echo   .venv\Scripts\python -m playwright install chromium
  pause
  exit /b 1
)

echo Starting SSU-TIME Everytime full crawl.
echo.
echo A browser will open.
echo Log in manually and complete 2-step verification.
echo After you can see Everytime home or lecture page, return to this window and press Enter.
echo.

".venv\Scripts\python.exe" scrape_everytime.py --headful --manual-login

echo.
echo Crawl finished or stopped.
echo Results are in:
echo   %~dp0data\raw_reviews.jsonl
echo   %~dp0data\reviews.xlsx
echo   %~dp0data\scrape_status.json
pause
