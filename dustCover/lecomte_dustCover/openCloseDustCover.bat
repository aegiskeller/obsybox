@echo off
REM openClose.bat - Control dust cover via serial from Windows batch

REM === CONFIGURATION ===
set SERIAL_PORT=COM3
set BAUDRATE=115200

REM === ARGUMENT CHECK ===
if "%1"=="" (
    echo Usage: %~nx0 [open|close]
    exit /b 1
)
if /i not "%1"=="open" if /i not "%1"=="close" (
    echo Usage: %~nx0 [open|close]
    exit /b 1
)

REM === CHECK IF PORT EXISTS ===
python - <<END
import sys
import serial.tools.list_ports
if "%SERIAL_PORT%" not in [p.device for p in serial.tools.list_ports.comports()]:
    print("Error: Serial port %SERIAL_PORT% not found.")
    sys.exit(2)
END
if errorlevel 1 exit /b %errorlevel%

REM === SEND COMMAND ===
python - <<END
import serial, time
ser = serial.Serial("%SERIAL_PORT%", %BAUDRATE%, timeout=2)
cmd = "COMMAND:OPEN" if "%1"=="open" else "COMMAND:CLOSE"
ser.write((cmd + "\n").encode("utf-8"))
print("Sent:", cmd)
start = time.time()
while time.time() - start < 3:
    if ser.in_waiting:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        print("Received:", line)
        if "RESULT:STATE" in line or "ERROR" in line:
            break
ser.close()
END
exit /b %errorlevel%