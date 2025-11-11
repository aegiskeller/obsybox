@echo off
echo Starting obsybox InfluxDB Dashboard...
echo.

cd /d %~dp0

REM Check if virtual environment exists
if exist "venv\Scripts\python.exe" (
    echo Using virtual environment...
    echo Starting Flask server...
    echo Dashboard will be available at: http://localhost:5000
    echo Network access at: http://192.168.1.x:5000
    echo Press Ctrl+C to stop the server
    echo.
    venv\Scripts\python.exe app.py
) else (
    echo Virtual environment not found. Creating it now...
    python -m venv venv
    echo Installing dependencies...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    echo Starting Flask server...
    echo Dashboard will be available at: http://localhost:5000
    echo Press Ctrl+C to stop the server
    echo.
    venv\Scripts\python.exe app.py
)

pause
