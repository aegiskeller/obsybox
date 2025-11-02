@echo off
REM Register ArduSafeMon ASCOM Driver - Run as Administrator
echo Registering ArduSafeMon ASCOM Driver...
echo.

REM Navigate to the correct directory
cd /d "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"

REM Check if DLL exists
if not exist "bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll" (
    echo ERROR: DLL not found! Please build the project first.
    echo Expected: bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll
    pause
    exit /b 1
)

REM Register the DLL using regasm
echo Registering COM component...
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\regasm.exe "bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll" /codebase

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: ArduSafeMon ASCOM Driver registered successfully!
    echo You can now use it in NINA or other ASCOM applications.
    echo.
    echo The driver should appear as:
    echo "ASCOM.ArduSafeMon.SafetyMonitor"
    echo.
) else (
    echo.
    echo ERROR: Failed to register driver
    echo Make sure you are running as Administrator
    echo.
)

echo Press any key to continue...
pause >nul