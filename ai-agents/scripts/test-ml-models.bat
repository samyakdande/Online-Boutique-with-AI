@echo off
echo 🤖 Testing ML Models MCP server functionality...

echo ⏳ Starting ML Models MCP server...
docker-compose -f docker-compose.simple.yml up -d ml-models-mcp

echo ⏳ Waiting for server to start...
ping 127.0.0.1 -n 16 > nul

echo 🔍 Running ML Models MCP tests...
docker-compose -f docker-compose.simple.yml run --rm -e ENVIRONMENT=development test-runner python scripts/test-ml-models-simple.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ ML Models MCP server tests passed!
    echo 🤖 Your ML Models MCP Server is working!
    echo 🔗 Test it at: http://localhost:8082/health
) else (
    echo ❌ ML Models MCP server tests failed!
    echo 📋 Check logs: scripts\logs.bat
    exit /b 1
)