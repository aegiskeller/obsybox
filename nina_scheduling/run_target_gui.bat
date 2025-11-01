@echo off
REM NINA Target Selector GUI Launcher
REM This script activates the virtual environment and runs the target selector GUI

cd /d "C:\Users\aegis\Documents\obsybox\nina_scheduling"

REM Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo Error: Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then install requirements: .\venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

REM Run the GUI using the virtual environment's Python
echo Starting NINA Target Selector GUI...
"C:\Users\aegis\Documents\obsybox\nina_scheduling\venv\Scripts\python.exe" target_selector_gui.py

REM If the GUI exits with an error, pause to show the error
if errorlevel 1 (
    echo.
    echo GUI exited with an error. Press any key to close this window.
    pause >nul
)