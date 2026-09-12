@echo off
setlocal
title CineSense AI - Repair Environment

echo.
echo ========================================
echo      CineSense AI Environment Repair
echo ========================================
echo.

if exist backend\.venv (
  echo Removing the old backend virtual environment...
  rmdir /s /q backend\.venv
)

echo Old virtual environment removed.
echo A new compatible environment will now be created.
echo.

call start_windows.bat
