@echo off
REM Deploy PAWS Modal Endpoint (Windows)

echo 🚀 Deploying PAWS Vision Engine to Modal.com...
echo.

REM Check if Modal is installed
modal --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Modal CLI not found. Installing...
    pip install modal
)

REM Check authentication
echo 🔐 Checking Modal authentication...
modal token check
if errorlevel 1 (
    echo ⚠️ Not authenticated. Opening browser...
    modal token new
)

REM Deploy to Modal
echo.
echo 📦 Deploying modal_inference.py...
cd /d "%~dp0backend_fastapi"
modal deploy modal_inference.py

echo.
echo ✅ Deployment complete!
echo.
echo 📝 Next steps:
echo 1. Copy the endpoint URL from above
echo 2. Update MODAL_API_URL in backend_fastapi/main.py
echo 3. Restart your backend server
echo.
echo 🎯 Test your deployment:
echo    modal logs paws-vision-engine
echo.

pause
