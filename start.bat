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
echo      [1] START MJ
echo      [2] STOP MJ
echo      [3] RESTART MJ
echo      [4] EXIT
echo.
set /p choice="    Select option (1-4): "

if "%choice%"=="1" goto START
if "%choice%"=="2" goto STOP
if "%choice%"=="3" goto RESTART
if "%choice%"=="4" exit
goto MENU

:START
echo.
echo    Starting Ollama...
start "" /min cmd /c "ollama serve"
timeout /t 2 >nul

echo    Starting MJ Backend on http://localhost:8000...
cd /d "%~dp0backend"
start "MJ-Backend" /min cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

echo    Opening MJ in browser...
timeout /t 3 >nul
start "" "http://localhost:8000"

echo.
echo    MJ is ONLINE!
timeout /t 2 >nul
goto MENU

:STOP
echo.
echo    Stopping MJ Backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
echo    Stopping Ollama...
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
start "" /min cmd /c "ollama serve"
timeout /t 2 >nul
cd /d "%~dp0backend"
start "MJ-Backend" /min cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"
timeout /t 3 >nul
start "" "http://localhost:8000"
echo.
echo    MJ Restarted!
timeout /t 2 >nul
goto MENU
