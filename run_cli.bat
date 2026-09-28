@echo off
REM Stone Halftone Engraver - Run CLI with sample image
REM This batch file runs the command-line interface for batch processing

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Stone Halftone Engraver CLI
echo   Command-line Processing
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Activate virtual environment
if exist ".venv" (
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment not found. Installing dependencies...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install --upgrade pip setuptools wheel -q
    pip install -r requirements.txt -q
)

REM Create output directory
if not exist "output" mkdir output

REM Run CLI with sample parameters
echo [INFO] Running CLI with sample parameters...
echo.

if not exist "sample\test.png" (
    echo [INFO] Creating sample image...
    python -c "from PIL import Image, ImageDraw; import os; os.makedirs('sample', exist_ok=True); img = Image.new('L', (400, 400), 255); draw = ImageDraw.Draw(img); [draw.line((i, 0, i, 400), fill=150, width=3) for i in range(0, 400, 20)]; [draw.line((0, i, 400, i), fill=150, width=3) for i in range(0, 400, 20)]; [draw.ellipse((x, y, x+16, y+16), fill=40) for y in range(80, 320, 30) for x in range(80, 320, 30)]; img.save('sample/test.png'); print('[OK] Sample image created')"
)

python src\stone_halftone.py ^
    --input sample\test.png ^
    --output output\test.nc ^
    --preview output\test_preview.png ^
    --brightness 1.0 ^
    --contrast 1.4 ^
    --cell-size-mm 3.0 ^
    --tool-diameter-mm 1.2 ^
    --dwell-s 0.08

if errorlevel 1 (
    echo.
    echo [ERROR] CLI processing failed
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Processing completed!
echo Output files:
echo   - G-code: output\test.nc
echo   - Preview: output\test_preview.png
echo.
pause
exit /b 0
