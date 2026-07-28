@echo off
REM Industrial Deep Diagnostic — Start All (Windows batch)
REM Starts both backend and frontend concurrently

setlocal enabledelayedexpansion

echo.
echo   ╔══════════════════════════════════════════════╗
echo   ║   Industrial Deep Diagnostic — Full Stack    ║
echo   ║   Backend:  http://localhost:3210             ║
echo   ║   Frontend: http://localhost:5180             ║
echo   ╚══════════════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [ERROR] Node.js is not installed. Please install Node.js ^>= 18.
    exit /b 1
)

echo   Node.js: 
node -v

REM Start backend in a new window
start "ind-diag-backend" cmd /c "%SCRIPT_DIR%start-backend.bat"

REM Small delay for backend to initialize
timeout /t 2 /nobreak >nul

REM Start frontend in a new window
start "ind-diag-frontend" cmd /c "%SCRIPT_DIR%start-frontend.bat"

echo.
echo   Both servers are starting.
echo   Open http://localhost:5180 in your browser.
echo   Close the server windows to stop all.
echo.

endlocal
