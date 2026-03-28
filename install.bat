@echo off
setlocal enableextensions

cd /d "%~dp0"

echo [1/5] Checking for Python...
where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found in PATH. Please install Python 3.10+ from https://www.python.org/downloads/
  exit /b 1
)

echo [2/5] Verifying Python version (3.10 or newer)...
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo Detected Python version is older than 3.10. Please upgrade Python.
  exit /b 1
)

echo [3/5] Creating virtual environment at .venv ...
python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Failed to create virtual environment.
  exit /b 1
)

echo [4/5] Upgrading pip...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo Failed to upgrade pip.
  exit /b 1
)

echo [5/5] Installing dependencies (PySide6, pynput)...
call ".venv\Scripts\python.exe" -m pip install PySide6 pynput
if errorlevel 1 (
  echo Failed to install dependencies.
  exit /b 1
)

echo.
echo Done. To activate the environment:
echo   PowerShell: .venv\Scripts\Activate.ps1
echo   CMD:        call .venv\Scripts\activate.bat
echo Then run the app with:
echo   python main.py

endlocal
