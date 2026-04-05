@echo off
REM Setup Learning Loop with Administrator Privileges
REM This batch file handles UAC elevation automatically

echo.
echo [INFO] Sports Prediction System - Automated Learning Setup
echo.

REM Check if running as admin
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Administrator privileges required!
    echo.
    echo Please run this script as Administrator:
    echo   1. Right-click this file
    echo   2. Select "Run as Administrator"
    echo.
    pause
    exit /b 1
)

echo [CHECK] Administrator privileges: OK
echo.

REM Run Python setup script
echo [ACTION] Running setup_automated_learning.py...
echo.

python scripts\setup_automated_learning.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Setup completed!
    echo.
    echo Next steps:
    echo   1. Verify: schtasks /query /tn "SportsPrediction\SportsPredictionSystem-DailyLearning"
    echo   2. View logs: Get-Content data/logs/automated/learning_loop_*.log -Tail 50
    echo   3. Test now: schtasks /run /tn "SportsPrediction\SportsPredictionSystem-DailyLearning"
    echo.
    pause
) else (
    echo.
    echo [ERROR] Setup failed with exit code %ERRORLEVEL%
    echo.
    pause
    exit /b 1
)
