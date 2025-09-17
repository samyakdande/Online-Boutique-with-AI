@echo off
echo 📊 Testing Analytics MCP server functionality...

echo ⏳ Starting Analytics MCP server...
docker-compose -f docker-compose.simple.yml up -d analytics-mcp

echo ⏳ Waiting for server to start...
ping 127.0.0.1 -n 16 > nul

echo 🔍 Running Analytics MCP tests...
docker-compose -f docker-compose.simple.yml run --rm -e ENVIRONMENT=development test-runner python scripts/test-analytics-simple.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ Analytics MCP server tests passed!
    echo 📊 Your Analytics MCP Server is working!
    echo 🔗 Test it at: http://localhost:8081/health
) else (
    echo ❌ Analytics MCP server tests failed!
    echo 📋 Check logs: scripts\logs.bat
    exit /b 1
)