@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo Run setup from README.md first.
  pause
  exit /b 1
)

echo Starting Everytime API crawl.
echo Make sure .env has EVERYTIME_COOKIE or curl txt files exist.
echo.

".venv\Scripts\python.exe" api_scrape_everytime.py

echo.
echo Done.
echo Results:
echo   %~dp0data\api_raw_reviews.jsonl
echo   %~dp0data\api_reviews.xlsx
echo   %~dp0data\api_scrape_status.json
pause
