@echo off
echo 💬 Testing Agent Communication Framework functionality...

echo 🔍 Running Agent Communication Framework tests...
docker-compose -f docker-compose.simple.yml run --rm -e ENVIRONMENT=development test-runner python scripts/test-communication-simple.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ Agent Communication Framework tests passed!
    echo 💬 Your Agent Communication Framework is working!
    echo 🔗 Agents can now communicate securely and efficiently
) else (
    echo ❌ Agent Communication Framework tests failed!
    echo 📋 Check logs for details
    exit /b 1
)