@echo off
REM Run Advanced Recommendation Agent Demo in Docker

echo ========================================
echo   Advanced Recommendation Agent Demo
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
powershell -Command "Start-Sleep -Seconds 10"

echo.
echo Running Advanced Recommendation Agent Demo...
echo.
docker-compose -f docker-compose.simple.yml --profile demo run --rm recommendation-demo

echo.
echo Demo completed! Cleaning up...
docker-compose -f docker-compose.simple.yml down

echo.
echo Press any key to exit...
pause >nul