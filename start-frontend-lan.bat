@echo off
cd /d "%~dp0"
python -m http.server 5500 --bind 0.0.0.0 --directory "%~dp0outputs\ssu-time-start-screen"
pause
