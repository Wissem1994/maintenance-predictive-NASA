@echo off
setlocal
cd /d "%~dp0.."
set "UV_CACHE_DIR=%CD%\.cache\uv"
set "UV_PYTHON_INSTALL_DIR=%CD%\.runtime\python"
if exist ".venv\Scripts\python.exe" goto dependencies
where uv >nul 2>nul
if errorlevel 1 goto pythonlauncher
uv venv --python 3.12 .venv
if errorlevel 1 exit /b 1
goto dependencies
:pythonlauncher
py -3.12 -m venv .venv
if errorlevel 1 (
  echo Python 3.12 requis. Consultez docs\installation.md
  exit /b 1
)
:dependencies
where uv >nul 2>nul
if errorlevel 1 goto pipinstall
uv pip install --python .venv\Scripts\python.exe -r backend\requirements-dev.txt
if errorlevel 1 exit /b 1
goto frontend
:pipinstall
".venv\Scripts\python.exe" -m pip install -r backend\requirements-dev.txt
if errorlevel 1 exit /b 1
:frontend
pushd frontend
call npm.cmd ci --cache ..\.cache\npm --no-audit --no-fund
if errorlevel 1 (popd & exit /b 1)
popd
".venv\Scripts\python.exe" -m scripts.init_db
