@echo off
:: Simple NINA Watchdog Launcher
:: Designed specifically for NINA External Script integration

:: Navigate to script directory
cd /d "C:\Users\aegis\Documents\obsybox\nina_watchdog"

:: Log the launch attempt
echo %DATE% %TIME% - NINA External Script called > nina_launch.log

:: Launch the watchdog directly without start command
"C:\Users\aegis\Documents\obsybox\nina_watchdog\venv\Scripts\python.exe" "C:\Users\aegis\Documents\obsybox\nina_watchdog\watchdog_safety_gui.py" --nina-mode

:: Exit with success code
exit /b 0