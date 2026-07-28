@echo off
REM Industrial Deep Diagnostic — Start Frontend (Windows batch)
REM Starts the Vue dev server on http://localhost:5180

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "FRONTEND_DIR=%PROJECT_ROOT%\app\frontend"

echo.
echo   Industrial Deep Diagnostic — Frontend
echo   =====================================
echo.

REM Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [ERROR] Node.js is not installed. Please install Node.js ^>= 18.
    pause
    exit /b 1
)

echo   Node.js:
node -v

REM Check if dependencies are installed
if not exist "%FRONTEND_DIR%\node_modules" (
    echo.
    echo   Dependencies not found. Installing...
    cd /d "%FRONTEND_DIR%" && call npm install
)

echo.
echo   Starting Vue dev server on http://localhost:5180
echo   Backend API proxy: /api ^> http://localhost:3210
echo   Press Ctrl+C to stop
echo.

cd /d "%FRONTEND_DIR%" && npx.cmd vite --host

pause
endlocal
