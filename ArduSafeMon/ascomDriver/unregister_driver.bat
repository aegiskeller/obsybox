@echo off
REM Unregister ArduSafeMon ASCOM Driver - Run as Administrator
echo Unregistering ArduSafeMon ASCOM Driver...
echo.

REM Navigate to the correct directory
cd /d "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"

REM Check if DLL exists
if not exist "bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll" (
    echo WARNING: DLL not found! 
    echo Expected: bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll
    echo Attempting to unregister anyway...
    echo.
)

REM Unregister the DLL using regasm
echo Unregistering COM component...
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\regasm.exe "bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll" /unregister

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: ArduSafeMon ASCOM Driver unregistered successfully!
    echo.
) else (
    echo.
    echo ERROR: Failed to unregister driver
    echo Make sure you are running as Administrator
    echo.
)

echo Press any key to continue...
pause >nul