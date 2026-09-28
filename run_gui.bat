@echo off
REM Stone Halftone Engraver - Run GUI on Windows
REM This batch file sets up Python environment and launches the GUI

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Stone Halftone Engraver
echo   PWM Vibration Motor Driver
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install/upgrade dependencies
echo [INFO] Installing/upgrading dependencies...
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Run GUI
echo [INFO] Launching Stone Halftone Engraver GUI...
echo.
python src\halftone_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] GUI encountered an error
    pause
    exit /b 1
)

echo.
echo [INFO] GUI closed successfully
pause
exit /b 0
