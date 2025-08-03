@echo off
echo 🎥 Ambient YouTube Player Setup
echo ===============================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.7+ from python.org
    pause
    exit /b 1
)

echo ✅ Python found!
echo.

echo Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ FFmpeg not found! 
    echo Please install FFmpeg from https://ffmpeg.org/download.html
    echo Or run: winget install FFmpeg
    pause
    exit /b 1
)

echo ✅ FFmpeg found!
echo.

echo Installing Python dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ✅ Setup complete!
echo.
echo To start the application, run:
echo python app.py
echo.
echo Then open your browser to: http://127.0.0.1:5000
echo.
pause
