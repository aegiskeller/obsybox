# ArduSafeMon ASCOM SafetyMonitor Driver

ASCOM SafetyMonitor driver for ArduSafeMon weather safety monitoring system. Integrates with NINA and other ASCOM-compatible astronomy software.

## Overview

This driver enables ASCOM applications (like NINA) to query the safety status from your ArduSafeMon Arduino-based weather monitor via serial communication. It implements the ASCOM ISafetyMonitorV3 interface.

## Requirements

- **Windows OS** (ASCOM is Windows-only)
- **ASCOM Platform 6.6** or later ([Download here](https://ascom-standards.org/Downloads/Index.htm))
- **Arduino running ArduSafeMon firmware** connected via USB/Serial
- **.NET Framework 4.8** (included with Windows 10/11)
- **Visual Studio 2019 or 2022** (for building from source)

## Arduino Setup

Your Arduino must be running the ArduSafeMon firmware that responds to the `S#` command:
- Send: `S#`
- Receive: `safe#` or `notsafe#`

The firmware at `ArduSafeMon_R4wifi_weather/ArduSafeMon_R4wifi/ArduSafeMon_R4wifi.ino` already implements this protocol.

### Verify Arduino Communication

1. Open Arduino IDE Serial Monitor (9600 baud)
2. Type `S#` and press Enter
3. You should see `safe#` or `notsafe#` response
4. Note the COM port number (e.g., COM3)

## Building the Driver

### Using Visual Studio

1. Open `ArduSafeMon.csproj` in Visual Studio
2. Restore NuGet packages (right-click solution → Restore NuGet Packages)
3. Build Solution (F6 or Build → Build Solution)
4. Output DLL will be in `bin\Debug\` or `bin\Release\`

### Using Command Line

```powershell
# Navigate to the driver directory
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"

# Restore packages and build
dotnet build ArduSafeMon.csproj -c Release
```

## Installation

### Manual Registration (Recommended for Development)

1. Build the driver (see above)
2. Open **PowerShell as Administrator**
3. Navigate to the build output directory
4. Register the COM DLL:

```powershell
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release"

# Register the driver with Windows COM
regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
```

### Verify Installation

1. Open **ASCOM Diagnostics** (Start Menu → ASCOM → Diagnostics)
2. Click "Choose Device" under SafetyMonitor
3. You should see "ArduSafeMon Safety Monitor" in the list

## Configuration

### First-Time Setup

1. Open ASCOM Device Chooser (or from NINA: Options → Equipment → Safety Monitor)
2. Select **ArduSafeMon Safety Monitor**
3. Click **Properties** button
4. Select your Arduino's COM port from the dropdown
5. Enable "Trace on" for debugging (optional)
6. Click **OK**

### COM Port Selection

The driver automatically lists all available COM ports. Select the one your Arduino is connected to. If unsure:

1. Open Device Manager (Windows)
2. Expand "Ports (COM & LPT)"
3. Look for "Arduino" or "USB Serial Device"
4. Note the COM port number

## Using with NINA

1. Open NINA
2. Go to **Options → Equipment → Safety Monitor**
3. Click **Choose Device**
4. Select **ArduSafeMon Safety Monitor**
5. Click **Connect**
6. The safety status will appear in NINA's equipment panel

### Safety Monitor Integration

- NINA will automatically query the safety status every few seconds
- If status becomes "Unsafe", NINA can:
  - Park the telescope
  - Close the dome/roof
  - Stop the current sequence
  - Warm up the camera

Configure these actions in NINA under **Options → Safety → Safety Monitor Settings**.

## Troubleshooting

### Driver Not Appearing in ASCOM Chooser

- Verify ASCOM Platform 6.6+ is installed
- Run `regasm` command as Administrator
- Check Windows Event Viewer for registration errors

### "Cannot connect to COM port" Error

- Verify Arduino is plugged in and drivers are installed
- Check COM port in Device Manager
- Close Arduino IDE Serial Monitor (it locks the port)
- Try a different USB cable or port
- Restart Windows to release stuck serial ports

### "Timeout reading from Arduino" Error

- Verify Arduino is running ArduSafeMon firmware
- Test with Serial Monitor: send `S#`, expect `safe#` or `notsafe#`
- Check baud rate is 9600 in Arduino code
- Increase read timeout in `Driver.cs` if needed

### Driver Connects but Wrong Status

- Check Arduino web interface (http://192.168.1.99) for current status
- Review detailed output in Serial Monitor after `S#` command
- Enable "Trace on" in driver setup and check ASCOM logs:
  - Location: `C:\Users\<username>\Documents\ASCOM\Logs`

### Serial Port Held After NINA Disconnect

This is a known issue with ASCOM serial drivers:

1. Close NINA completely
2. Open Device Manager → Ports
3. Right-click the Arduino port → Disable Device
4. Wait 5 seconds
5. Right-click again → Enable Device
6. Or use USB Device Tree Viewer to reset the port

## Development & Debugging

### Enable Tracing

1. In driver setup, check "Trace on"
2. Logs are written to: `C:\Users\<username>\Documents\ASCOM\Logs\ArduSafeMon.log`
3. View real-time with PowerShell:

```powershell
Get-Content "$env:USERPROFILE\Documents\ASCOM\Logs\ArduSafeMon.log" -Wait -Tail 20
```

### Testing Without NINA

Use ASCOM's built-in test tools:

1. Open **ASCOM Diagnostics**
2. Select **SafetyMonitor** tab
3. Choose **ArduSafeMon Safety Monitor**
4. Click **Connect**
5. Click **Read IsSafe** to test communication

### Modifying the Driver

The driver consists of:
- `Driver.cs` - Main ASCOM interface implementation
- `SetupDialogForm.cs/.Designer.cs` - Configuration UI
- `AssemblyInfo.cs` - Version and COM registration info

After modifications:
1. Rebuild the solution
2. Close all ASCOM applications
3. Re-register: `regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll`

## Technical Details

### ASCOM Interface

- **Interface**: ISafetyMonitorV3
- **ProgID**: `ASCOM.ArduSafeMon.SafetyMonitor`
- **GUID**: `A1B2C3D4-E5F6-4A5B-9C8D-7E6F5A4B3C2D`

### Communication Protocol

- **Baud Rate**: 9600
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Timeout**: 2000ms
- **Command**: `S#`
- **Response**: `safe#` or `notsafe#`

The driver automatically refreshes the safety state if it's older than 5 seconds when queried.

### Error Handling

The driver handles:
- Serial port connection failures
- Timeout on Arduino communication
- Unexpected response formats
- Port busy/unavailable conditions

All errors are logged to ASCOM trace files when tracing is enabled.

## Uninstallation

```powershell
# Run as Administrator
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release"
regasm /unregister ASCOM.ArduSafeMon.SafetyMonitor.dll
```

Then delete the driver files.

## License

See LICENSE file in repository root.

## Support

For issues, see the main obsybox repository: https://github.com/aegiskeller/obsybox

## Version History

### v1.0.0 (2025-10-28)
- Initial release
- Serial communication support
- ASCOM ISafetyMonitorV3 implementation
- NINA integration
- COM port auto-detection
