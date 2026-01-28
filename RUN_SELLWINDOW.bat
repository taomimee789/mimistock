@echo off
setlocal
cd /d "%~dp0"

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] à¹„à¸¡à¹ˆà¸žà¸š .venv\Scripts\python.exe
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "SellWindow.py"

