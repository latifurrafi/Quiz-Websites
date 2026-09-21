@echo off
REM Start the AI Club quiz without Docker, on Windows.
REM
REM   run.bat
REM
REM Creates a virtual environment, installs dependencies, prepares the
REM database and starts the server. Safe to run repeatedly.

setlocal
cd /d "%~dp0"

if "%PORT%"=="" set PORT=8000

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Install Python 3.12+ from https://www.python.org/downloads/
    echo Make sure you tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.12 or newer is required.
    python --version
    pause
    exit /b 1
)

if not exist ".venv" (
    echo ==^> Creating the virtual environment ^(first run only^)
    python -m venv .venv
)

echo ==^> Installing dependencies
call .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
call .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

echo ==^> Preparing the database
call .venv\Scripts\python.exe manage.py migrate --noinput

echo ==^> Checking for a quiz
call .venv\Scripts\python.exe manage.py seed_quiz --if-empty

echo ==^> Checking for an admin account
call .venv\Scripts\python.exe manage.py ensure_admin

echo.
echo   ---------------------------------------------------------
echo    Quiz          http://127.0.0.1:%PORT%
echo    Admin panel   http://127.0.0.1:%PORT%/admin/
echo.
echo    Press Ctrl+C to stop.
echo   ---------------------------------------------------------
echo.

call .venv\Scripts\python.exe manage.py runserver 0.0.0.0:%PORT%
endlocal
