@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Local preview is not prepared. Please read FORDEV.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\local_preview.py" start
pause
