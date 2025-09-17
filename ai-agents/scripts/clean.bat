@echo off
echo 🧹 Cleaning up containers and images...
docker-compose down -v --remove-orphans
docker system prune -f
if %errorlevel% equ 0 (
    echo ✅ Cleanup completed!
) else (
    echo ❌ Cleanup failed!
    exit /b 1
)