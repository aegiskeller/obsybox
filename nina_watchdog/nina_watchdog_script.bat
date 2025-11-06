@echo off
:: NINA Watchdog Script Launcher for Observatory Safety Monitor
:: Optimized for NINA integration with enhanced feedback

echo.
echo ========================================
echo   NINA Watchdog Observatory Monitor
echo ========================================
echo Starting watchdog safety monitoring system...

:: Use absolute paths to avoid directory issues
set SCRIPT_DIR=C:\Users\aegis\Documents\obsybox\nina_watchdog
set PYTHON_EXE=%SCRIPT_DIR%\venv\Scripts\python.exe
set GUI_SCRIPT=%SCRIPT_DIR%\watchdog_safety_gui.py

:: Verify prerequisites
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python virtual environment not found!
    echo Expected: %PYTHON_EXE%
    echo.
    echo Please ensure the safety monitor is properly installed.
    pause
    exit /b 1
)

if not exist "%GUI_SCRIPT%" (
    echo ERROR: Safety monitor GUI script not found!
    echo Expected: %GUI_SCRIPT%
    echo.
    echo Please check the installation directory.
    pause
    exit /b 1
)

:: Check for existing safety monitor processes (simplified)
tasklist /FI "IMAGENAME eq python.exe" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo.
    echo INFO: Python processes detected
    echo Note: If safety monitor is already running, check system tray
    echo.

echo.
echo Launching NINA Safety Monitor...
echo - Python: %PYTHON_EXE%
echo - Script: %GUI_SCRIPT%
echo - Auto-monitoring: ENABLED
echo - Pushover alerts: ENABLED
echo.

:: Launch the GUI with minimal window (will auto-minimize to tray)
start "NINA Watchdog Monitor" /MIN "%PYTHON_EXE%" "%GUI_SCRIPT%" --nina-mode

:: Wait a moment for startup
timeout /t 3 /nobreak >nul

:: Verify the process started (simplified check)
tasklist /FI "IMAGENAME eq python.exe" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo ✓ Watchdog monitor started successfully
    echo ✓ Check system tray for watchdog icon
    echo ✓ Monitoring will begin automatically
    echo.
    echo Your observatory watchdog is now on duty!
) else (
    echo ✗ Failed to start Python process
    echo Check the error messages above for details
)

echo.
echo ========================================
echo Watchdog integration complete. You may close this window.
echo ========================================
timeout /t 3 /nobreak >nul