@echo off
REM NINA Target Selector GUI Launcher
REM This script activates the virtual environment and runs the target selector GUI
REM Updated to handle PowerShell execution issues and provide better error handling

title NINA Target Selector - Starting...

REM Change to the script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo.
    echo ERROR: Virtual environment not found!
    echo.
    echo The virtual environment should be located at:
    echo   %~dp0venv\
    echo.
    echo To create it, run these commands:
    echo   cd "%~dp0"
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Check if GUI file exists
if not exist "target_selector_gui.py" (
    echo.
    echo ERROR: target_selector_gui.py not found!
    echo.
    echo Please ensure you're running this from the correct directory:
    echo   %~dp0
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Display startup information
echo.
echo ================================================================================
echo  NINA Target Selector GUI Launcher
echo ================================================================================
echo.
echo Starting GUI with enhanced features:
echo   * Persistent configuration storage
echo   * Timezone-aware observation night calculation (UTC+10)
echo   * Automatic date field override for var.astro.cz
echo   * Cache management and reset options
echo.
echo Location: %CD%
echo Python:   venv\Scripts\python.exe
echo Script:   target_selector_gui.py
echo.

REM Update window title
title NINA Target Selector GUI - Running

REM Run the GUI using the virtual environment's Python
REM Use full path to avoid PowerShell conflicts
"%~dp0venv\Scripts\python.exe" "%~dp0target_selector_gui.py"

REM Check exit code and handle errors
if errorlevel 1 (
    echo.
    echo ================================================================================
    echo  GUI EXITED WITH ERROR
    echo ================================================================================
    echo.
    echo The GUI encountered an error. Common issues:
    echo.
    echo 1. Missing Python packages:
    echo    Solution: venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    echo 2. Import errors (selenium, astropy, etc.):
    echo    Solution: Check virtual environment is properly set up
    echo.
    echo 3. Configuration file issues:
    echo    Solution: Delete user_config.json and restart
    echo.
    echo 4. Permission issues:
    echo    Solution: Run as administrator or check file permissions
    echo.
    echo Press any key to close this window...
    pause >nul
) else (
    echo.
    echo GUI closed normally.
)