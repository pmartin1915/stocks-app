@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Asymmetric DEV MODE
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

REM Check Poetry
poetry --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Poetry not found. Run: pip install poetry
    pause
    exit /b 1
)
echo [OK] Poetry found

REM Check .env exists
if not exist ".env" (
    echo.
    echo [ERROR] .env file not found!
    echo Run start.bat first for setup instructions.
    echo.
    pause
    exit /b 1
)
echo [OK] .env found

REM Check SEC_IDENTITY is configured
findstr /C:"your-email@domain.com" .env >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [ERROR] SEC_IDENTITY not configured.
    echo Run start.bat first for setup instructions.
    echo.
    pause
    exit /b 1
)
echo [OK] SEC_IDENTITY configured

REM Check database exists
if not exist "data\asymmetric.db" (
    echo.
    echo [ERROR] Database not initialized.
    echo Run start.bat first to initialize the database.
    echo.
    pause
    exit /b 1
)
echo [OK] Database found

REM Show status
echo.
echo ----------------------------------------
poetry run asymmetric status
echo ----------------------------------------

echo.
echo Starting MCP Server (port 8765)...
start "Asymmetric MCP Server" cmd /k "cd /d "%~dp0" && poetry run asymmetric mcp start --transport http"

REM Give MCP server time to start
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo   Services Running:
echo ----------------------------------------
echo   MCP Server:  http://localhost:8765
echo   Dashboard:   http://localhost:8501
echo ========================================
echo.
echo Close this window to stop the dashboard.
echo Close the "Asymmetric MCP Server" window to stop MCP.
echo.

REM Launch dashboard
poetry run streamlit run dashboard/app.py --server.headless false

echo.
echo Dashboard stopped.
echo NOTE: MCP server may still be running in separate window.
pause
