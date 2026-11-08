@echo off
setlocal
cd /d "%~dp0..\frontend"
if not exist node_modules (
  echo Dependances absentes. Executez scripts\setup.cmd
  exit /b 1
)
call npm.cmd run dev -- --port 5173 --strictPort
