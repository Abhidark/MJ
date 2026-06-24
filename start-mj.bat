@echo off
title MJ-Assistant Launcher
echo ========================================
echo   MJ-Assistant - Starting All Services
echo ========================================
echo.

:: Start Backend in new window
echo Starting Backend (port 8000)...
start "MJ-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait 6 seconds for backend to fully initialize
echo Waiting for backend to initialize...
timeout /t 6 /nobreak >nul

:: Start React Frontend in new window
echo Starting React Frontend (port 3000)...
start "MJ-React" cmd /k "cd /d %~dp0frontend-react && npm run dev"

echo.
echo Both services started!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul
start http://localhost:3000
exit
