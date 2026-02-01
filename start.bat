@echo off
setlocal enabledelayedexpansion

REM ========================================
REM   Asymmetric Investment Workstation
REM   Launcher for humans and Claude
REM ========================================

REM Parse arguments
set QUIET=false
set NO_BROWSER=false
set BACKGROUND=false
for %%A in (%*) do (
    if "%%A"=="--quiet" set QUIET=true
    if "%%A"=="-q" set QUIET=true
    if "%%A"=="--no-browser" set NO_BROWSER=true
    if "%%A"=="--background" set BACKGROUND=true
)

if "%QUIET%"=="false" (
    echo ========================================
    echo   Asymmetric Investment Workstation
    echo ========================================
    echo.
)

REM Change to script directory
cd /d "%~dp0"

REM Validate Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+
    if "%QUIET%"=="false" pause
    exit /b 1
)
if "%QUIET%"=="false" echo [OK] Python found

REM Validate Poetry
poetry --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Poetry not found. Run: pip install poetry
    if "%QUIET%"=="false" pause
    exit /b 1
)
if "%QUIET%"=="false" echo [OK] Poetry found

REM Check if .env exists (warn but don't fail)
if not exist ".env" (
    if "%QUIET%"=="false" echo [WARN] .env file not found - some features may not work
)

REM Build launch command
set LAUNCH_CMD=poetry run asymmetric launch
if "%QUIET%"=="true" set LAUNCH_CMD=!LAUNCH_CMD! --quiet
if "%NO_BROWSER%"=="true" set LAUNCH_CMD=!LAUNCH_CMD! --no-browser
if "%BACKGROUND%"=="true" set LAUNCH_CMD=!LAUNCH_CMD! --background

if "%QUIET%"=="false" (
    echo.
    echo Starting dashboard...
    echo.
)

REM Launch
%LAUNCH_CMD%
set LAUNCH_EXIT=%ERRORLEVEL%

REM Exit handling
if %LAUNCH_EXIT% neq 0 (
    echo [ERROR] Dashboard failed to start (exit code: %LAUNCH_EXIT%)
    if "%QUIET%"=="false" pause
    exit /b %LAUNCH_EXIT%
)

if "%QUIET%"=="false" (
    if "%BACKGROUND%"=="false" (
        echo.
        echo Dashboard stopped.
        pause
    )
)
exit /b 0
