@echo off
setlocal EnableExtensions
title CineSense AI

rem Always run relative to this script, even when it is opened from elsewhere.
cd /d "%~dp0"

echo.
echo ========================================
echo         CineSense AI Launcher
echo ========================================
echo.

rem Find a working Python 3.11+ interpreter. The direct-path fallbacks also
rem handle terminals that were opened before Python updated the user PATH.
set "PYTHON_EXE="
set "PYTHON_ARGS="

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_EXE=python"

if not defined PYTHON_EXE (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
  )
)

if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Launcher\py.exe" (
  "%LocalAppData%\Programs\Python\Launcher\py.exe" -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Launcher\py.exe"
    set "PYTHON_ARGS=-3"
  )
)

if not defined PYTHON_EXE (
  for /d %%D in ("%LocalAppData%\Programs\Python\Python*") do (
    if exist "%%~fD\python.exe" call :select_python "%%~fD\python.exe"
  )
)

if not defined PYTHON_EXE (
  echo [ERROR] Python 3.11 or newer was not found.
  echo Install Python from https://www.python.org/downloads/windows/
  echo During installation, select "Add Python to PATH", then reopen this launcher.
  pause
  exit /b 1
)

rem npm.cmd avoids PowerShell execution-policy issues. Add Node's standard
rem install directory when this terminal has an old PATH.
call npm.cmd --version >nul 2>nul
if errorlevel 1 if exist "%ProgramFiles%\nodejs\npm.cmd" set "PATH=%ProgramFiles%\nodejs;%PATH%"

call npm.cmd --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js/npm was not found.
  echo Install Node.js 20 or newer from https://nodejs.org/
  echo Then reopen this launcher.
  pause
  exit /b 1
)

echo Using:
"%PYTHON_EXE%" %PYTHON_ARGS% --version
node --version
echo.

if /i "%~1"=="--check" (
  echo Launcher prerequisite check passed.
  exit /b 0
)

if not exist backend\.env copy backend\.env.example backend\.env >nul
if not exist backend\.venv\Scripts\python.exe (
  echo Creating backend virtual environment...
  "%PYTHON_EXE%" %PYTHON_ARGS% -m venv backend\.venv
  if errorlevel 1 (
    echo [ERROR] Could not create the backend virtual environment.
    pause
    exit /b 1
  )
)

echo Checking backend dependencies...
backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Backend dependency installation failed.
  pause
  exit /b 1
)

if not exist frontend\node_modules (
  echo Installing frontend dependencies...
  pushd frontend
  call npm.cmd install
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
start "CineSense Backend" "%ComSpec%" /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting CineSense frontend...
start "CineSense Frontend" "%ComSpec%" /k "cd /d ""%~dp0frontend"" && call npm.cmd run dev"

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
exit /b 0

:select_python
if defined PYTHON_EXE exit /b 0
"%~1" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "PYTHON_EXE=%~1"
exit /b 0
