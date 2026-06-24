@echo off
echo Stopping MJ Assistant...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /F >nul 2>&1
taskkill /IM "ollama.exe" /F >nul 2>&1
echo MJ is OFFLINE.
pause
