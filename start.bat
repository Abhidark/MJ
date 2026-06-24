@echo off
color 0C
title MJ Assistant Control Panel
:MENU
cls
echo.
echo    ========================================
echo    ^|        MJ ASSISTANT v2.0             ^|
echo    ^|     Your Personal AI Assistant       ^|
echo    ========================================
echo.
echo      [1] START MJ (Groq Cloud)
echo      [2] START MJ + Ollama (Local AI)
echo      [3] STOP MJ
echo      [4] RESTART MJ
echo      [5] EXIT
echo.
set /p choice="    Select option (1-5): "

if "%choice%"=="1" goto START_GROQ
if "%choice%"=="2" goto START_OLLAMA
if "%choice%"=="3" goto STOP
if "%choice%"=="4" goto RESTART
if "%choice%"=="5" exit
goto MENU

:START_GROQ
echo.
echo    Starting MJ Backend (Groq mode)...
cd /d "%~dp0backend"
start "MJ-Backend" /min cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

echo    Opening MJ in browser...
timeout /t 3 >nul
start "" "http://localhost:8000"

echo.
echo    MJ is ONLINE! (Provider: Groq Cloud)
timeout /t 2 >nul
goto MENU

:START_OLLAMA
echo.
echo    Starting Ollama...
start "" /min cmd /c "ollama serve"
timeout /t 2 >nul

echo    Starting MJ Backend...
cd /d "%~dp0backend"
start "MJ-Backend" /min cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

echo    Opening MJ in browser...
timeout /t 3 >nul
start "" "http://localhost:8000"

echo.
echo    MJ is ONLINE! (Provider: Ollama + Groq)
timeout /t 2 >nul
goto MENU

:STOP
echo.
echo    Stopping MJ Backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
echo    Stopping Ollama (if running)...
taskkill /IM "ollama.exe" /F >nul 2>&1
echo.
echo    MJ is OFFLINE.
timeout /t 2 >nul
goto MENU

:RESTART
echo.
echo    Restarting MJ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
taskkill /IM "ollama.exe" /F >nul 2>&1
timeout /t 2 >nul
cd /d "%~dp0backend"
start "MJ-Backend" /min cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
timeout /t 3 >nul
start "" "http://localhost:8000"
echo.
echo    MJ Restarted! (Provider: Groq Cloud)
timeout /t 2 >nul
goto MENU
