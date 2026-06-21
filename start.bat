@echo off
echo ================================
echo    MJ Assistant - Phase 1
echo ================================
echo.

echo [1] Starting backend on http://localhost:8000
cd /d "%~dp0backend"
start "MJ-Backend" cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

echo [2] Opening MJ Assistant in browser...
timeout /t 3 >nul
start "" "http://localhost:8000"

echo.
echo Done! Make sure Ollama is running: ollama run qwen2.5:1.5b
echo ================================
pause
