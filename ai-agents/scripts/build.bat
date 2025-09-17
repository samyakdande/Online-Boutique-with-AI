@echo off
echo 🔨 Building simple Docker image (no local Python needed)...
echo 📍 Current directory: %CD%
docker-compose -f docker-compose.simple.yml build
if %errorlevel% equ 0 (
    echo ✅ Docker image built successfully!
    echo 🚀 Ready to test! Run: scripts\test-mcp.bat
) else (
    echo ❌ Build failed!
    echo 💡 Make sure you're in the ai-agents directory
    exit /b 1
)