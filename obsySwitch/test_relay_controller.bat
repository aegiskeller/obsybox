@echo off
echo ObsyBox Relay Controller Test
echo =============================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or later
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking dependencies...
python -c "import requests; import json" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install required packages
        pause
        exit /b 1
    )
)

echo Running relay controller tests...
echo.
python test_relay_controller.py

echo.
echo Test completed. Check results above.
pause