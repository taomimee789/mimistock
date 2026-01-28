@echo off
setlocal
cd /d "%~dp0"

REM à¹ƒà¸Šà¹‰ UTF-8 à¹ƒà¸™ CMD à¹€à¸žà¸·à¹ˆà¸­à¹ƒà¸«à¹‰à¸ à¸²à¸©à¸²à¹„à¸—à¸¢à¹„à¸¡à¹ˆà¹€à¸›à¹‡à¸™à¸•à¹ˆà¸²à¸‡à¸”à¸²à¸§
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] à¹„à¸¡à¹ˆà¸žà¸š .venv\Scripts\python.exe
  echo à¸à¸£à¸¸à¸“à¸²à¸ªà¸£à¹‰à¸²à¸‡ venv à¸«à¸£à¸·à¸­à¹€à¸Šà¹‡à¸„ path à¹‚à¸›à¸£à¹€à¸ˆà¸à¸•à¹Œ
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "main.py"

