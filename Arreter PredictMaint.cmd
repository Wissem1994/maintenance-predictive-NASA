@echo off
setlocal
title PredictMaint AI - Arret
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\predictmaint.ps1" -Action Stop %*
if errorlevel 1 (
  echo.
  echo L'arret a echoue. Consultez le message ci-dessus.
  pause
  exit /b 1
)
