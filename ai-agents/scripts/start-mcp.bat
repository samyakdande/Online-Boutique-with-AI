@echo off
echo 🔌 Starting all MCP servers...
docker-compose -f docker-compose.simple.yml up -d boutique-api-mcp analytics-mcp ml-models-mcp
if %errorlevel% equ 0 (
    echo ✅ All MCP servers started!
    echo 📊 Boutique API MCP: http://localhost:8080
    echo 📈 Analytics MCP: http://localhost:8081
    echo 🤖 ML Models MCP: http://localhost:8082
    echo.
    echo 🔗 Health checks:
    echo   - Boutique API: http://localhost:8080/health
    echo   - Analytics: http://localhost:8081/health
    echo   - ML Models: http://localhost:8082/health
    echo.
    echo 🧪 To test:
    echo   - Boutique API: scripts\test-mcp.bat
    echo   - Analytics: scripts\test-analytics.bat
    echo   - ML Models: scripts\test-ml-models.bat
) else (
    echo ❌ Failed to start MCP servers!
    exit /b 1
)