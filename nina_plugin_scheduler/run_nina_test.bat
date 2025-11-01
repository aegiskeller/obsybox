@echo off
REM run_nina_test.bat - Simple batch file to run NINA scheduler test

echo ============================================
echo obsybox NINA Scheduler API Test
echo ============================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please ensure Python is installed and accessible
    pause
 exit /b 1
)

echo Checking NINA API connection...
python -c "import requests; requests.get('http://localhost:1888/v2/api/version', timeout=5)" 2>nul
if errorlevel 1 (
    echo WARNING: Cannot connect to NINA API
    echo Make sure NINA is running and API is enabled
    echo.
    set /p continue=Continue anyway? (y/N): 
    if /i not "!continue!"=="y" exit /b 1
)

echo.
echo Starting NINA scheduler test...
echo.

python test_nina_scheduler_api.py
set exitcode=%errorlevel%

echo.
if %exitcode%==0 (
    echo Test completed successfully!
    echo Check your Pushover notifications for test messages
) else (
    echo Test failed with exit code %exitcode%
)

echo.
echo Test Notes:
echo - This test only sends notifications (no hardware movement)
echo - Check NINA's log for any API errors  
echo - Modify test_config.json to customize test parameters
echo.
pause