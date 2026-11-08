@echo off
setlocal
title PredictMaint AI - Demarrage
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\predictmaint.ps1" -Action Start %*
if errorlevel 1 (
  echo.
  echo Le lancement a echoue. Consultez le message ci-dessus.
  pause
  exit /b 1
)
