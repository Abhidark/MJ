@echo off
title MJ-Assistant - Stopping
echo ========================================
echo   MJ-Assistant - Stopping All Services
echo ========================================
echo.

taskkill /FI "WINDOWTITLE eq MJ-Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MJ-React*" /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1

echo All MJ services stopped.
timeout /t 2 /nobreak >nul
exit
