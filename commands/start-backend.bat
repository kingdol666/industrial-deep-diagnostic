@echo off
REM Industrial Deep Diagnostic — Start Backend (Windows batch)
REM Starts the Express API server on http://localhost:3210

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "BACKEND_DIR=%PROJECT_ROOT%\app\backend"

echo.
echo   Industrial Deep Diagnostic — Backend
echo   ====================================
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
if not exist "%BACKEND_DIR%\node_modules" (
    echo.
    echo   Dependencies not found. Installing...
    cd /d "%BACKEND_DIR%" && call npm install
)

REM Ensure directories exist
if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"
if not exist "%PROJECT_ROOT%\workspace\diagnostic-runs" mkdir "%PROJECT_ROOT%\workspace\diagnostic-runs"

echo.
echo   Starting Express API server on http://localhost:3210
echo   Project root: %PROJECT_ROOT%
echo   Press Ctrl+C to stop
echo.

cd /d "%PROJECT_ROOT%" && node "%BACKEND_DIR%\src\index.mjs"

pause
endlocal
