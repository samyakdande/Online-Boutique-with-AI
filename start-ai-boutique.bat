@echo off
REM AI-Powered Online Boutique Startup Script for Windows
REM This script starts all AI agents and the Online Boutique services

echo 🚀 Starting AI-Powered Online Boutique...
echo ======================================

REM Check if .env file exists
if not exist .env (
    echo ⚠️  Creating .env file...
    (
        echo # Gemini API Configuration
        echo GEMINI_API_KEY=your_gemini_api_key_here
        echo.
        echo # MCP Server Configuration
        echo MCP_BOUTIQUE_PORT=8080
        echo MCP_ANALYTICS_PORT=8081
        echo MCP_ML_MODELS_PORT=8082
        echo.
        echo # A2A Protocol Configuration
        echo A2A_WEBSOCKET_PORT=9090
        echo.
        echo # Frontend Configuration
        echo FRONTEND_PORT=8080
        echo.
        echo # Development/Production Mode
        echo ENVIRONMENT=development
        echo DEBUG=true
    ) > .env
    echo 📝 Please edit .env file and add your GEMINI_API_KEY
    echo    You can get one from: https://makersuite.google.com/app/apikey
    pause
    exit /b 1
)

echo ✅ Environment configuration found

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo ✅ Docker is running

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ docker-compose is not available. Please install Docker Desktop.
    pause
    exit /b 1
)

echo ✅ docker-compose is available

REM Build and start services
echo.
echo 🔨 Building AI agents and services...
docker-compose -f docker-compose.ai-boutique.yml build

echo.
echo 🚀 Starting all services...
docker-compose -f docker-compose.ai-boutique.yml up -d

echo.
echo ⏳ Waiting for services to be ready...
timeout /t 30 /nobreak >nul

echo.
echo 🏥 Health checking services...
echo Checking services... (this may take a moment)

REM Simple health check using curl or powershell
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:8080' -UseBasicParsing -TimeoutSec 5 | Out-Null; Write-Host '✅ Frontend: Ready' } catch { Write-Host '⚠️  Frontend: Starting...' }"

echo.
echo 🎉 AI-Powered Online Boutique is starting!
echo ======================================
echo.
echo 🌐 Frontend: http://localhost:8080
echo 🔧 MCP Servers:
echo    - Boutique API: http://localhost:8080
echo    - Analytics: http://localhost:8081
echo    - ML Models: http://localhost:8082
echo.
echo 🤖 AI Agents:
echo    - Virtual Try-On: http://localhost:9001
echo    - Dynamic Pricing: http://localhost:9002
echo    - AI Chatbot: http://localhost:9003
echo    - Recommendations: http://localhost:9004
echo    - Marketing Email: http://localhost:9005
echo    - Review Tracker: http://localhost:9006
echo    - Personal Stylist: http://localhost:9007
echo.
echo 🔌 WebSocket Gateway: ws://localhost:9090
echo.
echo 📊 To view logs: docker-compose -f docker-compose.ai-boutique.yml logs -f
echo 🛑 To stop: docker-compose -f docker-compose.ai-boutique.yml down
echo.
echo 🎯 Try the AI features:
echo    1. Visit a product page and click 'Try On with AI'
echo    2. Use the AI chatbot in the bottom right
echo    3. Watch for dynamic pricing updates
echo    4. Get personalized recommendations
echo.
echo Opening browser...
start http://localhost:8080

pause