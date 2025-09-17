@echo off
REM Run Review Tracker Agent Demo in Docker
REM This script builds and runs the Review Tracker Agent demo using Docker Compose

echo ========================================
echo   Review Tracker Agent Demo (Docker)
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "docker-compose.simple.yml" (
    echo Error: Please run this script from the ai-agents directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if Docker is running
docker version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running or not installed
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo Building Docker images...
docker-compose -f docker-compose.simple.yml build

if errorlevel 1 (
    echo Error: Failed to build Docker images
    pause
    exit /b 1
)

echo.
echo Starting MCP servers...
docker-compose -f docker-compose.simple.yml up -d boutique-api-mcp analytics-mcp ml-models-mcp

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Running Review Tracker Agent Demo...
echo.
docker-compose -f docker-compose.simple.yml --profile demo run --rm review-tracker-demo

echo.
echo Demo completed! Cleaning up...
docker-compose -f docker-compose.simple.yml down

echo.
echo Press any key to exit...
pause >nul