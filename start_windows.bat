@echo off
setlocal EnableExtensions
title CineSense AI

echo.
echo ========================================
echo         CineSense AI Launcher
echo ========================================
echo.

where python >nul 2>nul || (echo [ERROR] Python not found. & pause & exit /b 1)
where npm >nul 2>nul || (echo [ERROR] Node.js/npm not found. & pause & exit /b 1)

for /f "delims=" %%V in ('python --version 2^>^&1') do set PYVER=%%V
echo Using %PYVER%
echo.

if not exist backend\.env copy backend\.env.example backend\.env >nul
if not exist backend\.venv\Scripts\python.exe (
  echo Creating backend virtual environment...
  python -m venv backend\.venv
)

echo Checking backend dependencies...
call backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependency installation failed.
  pause
  exit /b 1
)

if not exist frontend\node_modules (
  echo Installing frontend dependencies...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    echo [ERROR] Frontend dependency installation failed.
    pause
    exit /b 1
  )
  popd
)

echo.
echo Starting CineSense backend...
start "CineSense Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting CineSense frontend...
start "CineSense Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo CineSense AI is starting.
echo ========================================
echo Frontend: http://127.0.0.1:5173
echo API docs: http://127.0.0.1:8000/docs
echo.
echo IMPORTANT: Keep both backend and frontend windows open.
echo If the page was already open, press Ctrl+F5 once.
echo.
pause
