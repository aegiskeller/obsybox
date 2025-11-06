@echo off
:: NINA Watchdog Quick Launcher
:: Launches watchdog and returns immediately to NINA

:: Ensure we're in the correct directory
cd /d "C:\Users\aegis\Documents\obsybox\nina_watchdog"

:: Check if watchdog is already running
tasklist /FI "IMAGENAME eq python.exe" | findstr /C:"python.exe" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Watchdog may already be running - checking system tray
    exit /b 0
)

:: Launch watchdog in detached mode and return immediately
start /B "NINA Watchdog" "C:\Users\aegis\Documents\obsybox\nina_watchdog\venv\Scripts\python.exe" "C:\Users\aegis\Documents\obsybox\nina_watchdog\watchdog_safety_gui.py" --nina-mode

:: Give it a moment to start, then exit
timeout /t 1 /nobreak >nul

echo Watchdog launched successfully
exit /b 0