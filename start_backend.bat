@echo off
echo Starting PAWS Backend Server...
echo.

cd /d "%~dp0backend_fastapi"

echo Activating virtual environment...
call ..\.venv\Scripts\activate

echo Starting FastAPI server...
python main.py

pause
