@echo off
echo ========================================
echo Virtual Try-On Agent Demo
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "ai_agents" (
    echo Error: Please run this script from the ai-agents directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check for Gemini API key
if "%GEMINI_API_KEY%"=="" (
    echo Warning: GEMINI_API_KEY environment variable not set
    echo The demo will use mock data instead of real AI analysis
    echo.
    echo To use real Gemini AI, set your API key:
    echo set GEMINI_API_KEY=your-api-key-here
    echo.
    pause
)

echo Starting Virtual Try-On Agent Demo...
echo.

REM Run the demo
python scripts/demo_virtual_tryon.py

echo.
echo Demo completed!
pause