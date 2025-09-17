@echo off
REM Run Interactive Review Tracker Agent Demo in Docker

echo ========================================
echo   Interactive Review Tracker Demo
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "docker-compose.simple.yml" (
    echo Error: Please run this script from the ai-agents directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Building and starting services...
docker-compose -f docker-compose.simple.yml up -d boutique-api-mcp analytics-mcp ml-models-mcp

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Starting interactive demo...
echo Type your own reviews to analyze!
echo.
docker-compose -f docker-compose.simple.yml run --rm review-tracker-demo python scripts/demo_review_tracker.py --interactive

echo.
echo Cleaning up...
docker-compose -f docker-compose.simple.yml down

echo.
echo Press any key to exit...
pause >nul