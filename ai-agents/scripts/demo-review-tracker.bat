@echo off
REM Demo script for Review Tracker Agent
REM This script runs the Review Tracker Agent demo with sample reviews

echo ========================================
echo   Review Tracker Agent Demo
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "ai_agents" (
    echo Error: Please run this script from the ai-agents directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies if needed
echo Installing dependencies...
pip install -q -r requirements.txt

REM Check for Gemini API key
if "%GEMINI_API_KEY%"=="" (
    echo.
    echo WARNING: GEMINI_API_KEY environment variable is not set
    echo Please set your Gemini API key:
    echo   set GEMINI_API_KEY=your-api-key-here
    echo.
    echo You can get a free API key from: https://makersuite.google.com/app/apikey
    echo.
    set /p "api_key=Enter your Gemini API key (or press Enter to skip): "
    if not "!api_key!"=="" (
        set GEMINI_API_KEY=!api_key!
    )
)

echo.
echo Starting Review Tracker Agent Demo...
echo.

REM Run the demo
python scripts/demo_review_tracker.py

echo.
echo Demo completed!
echo.

REM Check if user wants to run interactive mode
set /p "interactive=Run interactive mode? (y/n): "
if /i "%interactive%"=="y" (
    echo.
    echo Starting interactive mode...
    python scripts/demo_review_tracker.py --interactive
)

echo.
echo Press any key to exit...
pause >nul