@echo off
setlocal
title CineSense AI - Apply Clean Backend Restart

echo.
echo ========================================
echo      CineSense Backend Clean Restart
echo ========================================
echo.

echo Closing this script does not delete your database.
echo.

if exist backend\.venv (
  echo Updating backend dependencies...
  call backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] Dependency update failed.
    pause
    exit /b 1
  )
)

echo.
echo Restarting CineSense using the normal launcher...
call start_windows.bat
