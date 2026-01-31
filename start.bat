@echo off
echo ========================================
echo   Asymmetric Investment Workstation
echo ========================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Just use the Python launch command - it handles everything
poetry run asymmetric launch

REM If we get here, dashboard stopped or errored
echo.
pause
