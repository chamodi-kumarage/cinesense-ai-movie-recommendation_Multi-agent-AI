@echo off
setlocal
title CineSense AI - Frontend Repair

echo.
echo ========================================
echo       CineSense AI Frontend Repair
echo ========================================
echo.
echo This removes only frontend dependencies and rebuilds them.
echo Your backend database and CineSense data are NOT deleted.
echo.

if exist frontend\node_modules (
  echo Removing old frontend node_modules...
  rmdir /s /q frontend\node_modules
)

if exist frontend\package-lock.json (
  del /q frontend\package-lock.json
)

pushd frontend
echo Installing clean frontend dependencies...
call npm install
if errorlevel 1 (
  popd
  echo [ERROR] npm install failed.
  pause
  exit /b 1
)
popd

echo Frontend repaired successfully.
echo Starting CineSense...
call start_windows.bat
