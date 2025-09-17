@echo off
echo 🧪 Testing MCP server functionality...

echo ⏳ Starting MCP server...
docker-compose -f docker-compose.simple.yml up -d boutique-api-mcp

echo ⏳ Waiting for server to start...
ping 127.0.0.1 -n 16 > nul

echo 🔍 Running MCP tests...
docker-compose -f docker-compose.simple.yml run --rm test-runner

if %errorlevel% equ 0 (
    echo.
    echo ✅ MCP server tests passed!
    echo 🎉 Your AI-Powered Boutique MCP Server is working!
) else (
    echo ❌ MCP server tests failed!
    echo 📋 Check logs: scripts\logs.bat
    exit /b 1
)