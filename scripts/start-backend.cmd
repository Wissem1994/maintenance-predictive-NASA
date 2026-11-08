@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Environnement absent. Executez scripts\setup.cmd
  exit /b 1
)
".venv\Scripts\python.exe" -m scripts.init_db
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
