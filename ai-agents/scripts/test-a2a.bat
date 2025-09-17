@echo off
echo 🔗 Testing A2A Protocol functionality...

echo 🔍 Running A2A Protocol tests...
docker-compose -f docker-compose.simple.yml run --rm -e ENVIRONMENT=development test-runner python scripts/test-a2a-simple.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ A2A Protocol tests passed!
    echo 🔗 Your A2A Protocol is working!
    echo 📋 Agent communication ready for deployment
) else (
    echo ❌ A2A Protocol tests failed!
    echo 📋 Check logs for details
    exit /b 1
)