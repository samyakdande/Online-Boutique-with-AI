@echo off
echo 🛑 Stopping MCP server...
docker-compose -f docker-compose.simple.yml down
if %errorlevel% equ 0 (
    echo ✅ MCP server stopped!
) else (
    echo ❌ Failed to stop server!
    exit /b 1
)