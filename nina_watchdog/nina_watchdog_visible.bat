@echo off
:: NINA Watchdog Script - GUI VISIBLE VERSION
:: Shows the GUI window immediately instead of hiding to system tray

:: Ensure we're in the correct directory
cd /d "C:\Users\aegis\Documents\obsybox\nina_watchdog"

echo.
echo ========================================
echo   NINA Watchdog - GUI Visible Mode
echo ========================================
echo Starting watchdog safety monitoring with visible GUI...
echo Working Directory: %CD%

:: Use absolute paths
set SCRIPT_DIR=C:\Users\aegis\Documents\obsybox\nina_watchdog
set PYTHON_EXE=%SCRIPT_DIR%\venv\Scripts\python.exe
set GUI_SCRIPT=%SCRIPT_DIR%\watchdog_safety_gui.py

echo.
echo Checking prerequisites...
echo Python EXE: %PYTHON_EXE%
echo GUI Script: %GUI_SCRIPT%
echo.

:: Verify prerequisites
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python virtual environment not found!
    echo Expected: %PYTHON_EXE%
    timeout /t 10 /nobreak >nul
    exit /b 1
)

if not exist "%GUI_SCRIPT%" (
    echo ERROR: Safety monitor GUI script not found!
    echo Expected: %GUI_SCRIPT%
    timeout /t 10 /nobreak >nul
    exit /b 1
)

echo.
echo Launching NINA Watchdog Monitor with VISIBLE GUI...
echo - Python: %PYTHON_EXE%
echo - Script: %GUI_SCRIPT%
echo - GUI Mode: VISIBLE (not hidden)
echo - Auto-monitoring: ENABLED
echo.

::ಮ Launch the GUI WITHOUT hidden flags - GUI will be visible but runs in background  
echo Starting watchdog GUI in visible mode (background process)...
start "NINA Watchdog Monitor" "%PYTHON_EXE%" "%GUI_SCRIPT%"

:: Brief pause to allow startup
timeout /t 2 /nobreak >nul

echo.
echo ✓ Watchdog GUI launched successfully in background
echo ✓ Check for visible GUI window on your desktop  
echo ✓ Monitoring will begin automatically
echo.
echo ========================================
echo Script completed - NINA can continue normally
echo ========================================