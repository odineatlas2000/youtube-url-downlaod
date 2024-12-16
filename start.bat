@echo off
echo Starting development environment...
echo.

:: Kill any processes using port 3002
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3002" ^| find "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)

:: Start the development environment
node start-dev.js
