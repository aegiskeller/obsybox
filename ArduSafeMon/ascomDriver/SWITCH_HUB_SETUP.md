# ASCOM Switch Hub - Setup Guide

## Overview
The Wombat Switch Hub combines sensor data from multiple sources into a single ASCOM Switch device:
- **ArduSafeMon Rain Sensor** (via serial COM port)
- **OPIR Sensor** (via HTTP at 192.168.1.101)

All sensors appear as gauges in NINA's Switch equipment panel.

## Sensors Exposed

| Switch ID | Name | Description | Range |
|-----------|------|-------------|-------|
| 0 | Rain Sensor | Rain sensor analog value (0-1023). Higher = damper | 0-1023 |
| 1 | Light (Lux) | Light intensity in lux. Higher = brighter | 0-100000 |
| 2 | Sky Temperature | Sky temperature from MLX90614 (°C). Lower = clearer | -40 to 50°C |
| 3 | Ambient Temperature | Ambient temperature from MLX90614 (°C) | -40 to 50°C |
| 4 | AHT10 Temperature | Temperature from AHT10 sensor (°C) | -40 to 50°C |
| 5 | AHT10 Humidity | Relative humidity from AHT10 (%). Lower = drier | 0-100% |

## Setup Instructions

### 1. Upload Arduino Firmware
Upload the updated `opir_sensor.ino` to your MKR WiFi 1010 (IP: 192.168.1.101). The firmware now includes HTTP endpoints:
- `/lux` - Returns lux value
- `/sky` - Returns sky temperature
- `/ambient` - Returns ambient temperature
- `/aht_temp` - Returns AHT10 temperature
- `/aht_humidity` - Returns AHT10 humidity

### 2. Configure NINA
1. Open NINA
2. Go to Equipment → Switch
3. Click the "+" button to add a new switch
4. Select "Wombat Switch Hub (All Sensors)"
5. Click "Connect"

The COM port is shared with the SafetyMonitor - configure it once in the SafetyMonitor setup.

### 3. Verify Operation
All 6 sensors should appear as gauges showing live values. Values update every 5 seconds (cached).

## Architecture

### Data Flow
```
ArduSafeMon (COM7)     OPIR Sensor (HTTP)
       ↓                      ↓
  SharedHardware         HttpClient
       ↓                      ↓
       └──────────┬───────────┘
                  ↓
           Switch Hub Driver
                  ↓
              NINA Gauges
```

### Files
- `SwitchHubDriver.cs` - Main switch hub implementation
- `SharedHardware.cs` - Serial communication with ArduSafeMon
- `opir_sensor.ino` - Arduino firmware with HTTP endpoints
- `RegisterSwitchHub.ps1` - ASCOM Profile registration script

## Troubleshooting

### Switch Hub doesn't appear in NINA
Run: `powershell -ExecutionPolicy Bypass -File .\RegisterSwitchHub.ps1`

### Rebuilding the driver
Use the newer MSBuild from Visual Studio 2022 (requires C# 7.3 support):
```powershell
cd C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver
& "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" ArduSafeMon.csproj /p:Configuration=Release /p:Platform=AnyCPU /t:Rebuild
Start-Process -FilePath "C:\Windows\Microsoft.NET\Framework\v4.0.30319\regasm.exe" -ArgumentList "/codebase","bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll" -Verb RunAs -Wait
powershell -ExecutionPolicy Bypass -File .\RegisterSwitchHub.ps1
```

### No values displaying
1. Check ASCOM logs in `C:\Users\<username>\Documents\ASCOM\Logs <date>\`
2. Look for `ASCOM.ArduSafeMon.SwitchHub.*.txt`
3. Verify OPIR sensor is accessible at http://192.168.1.101
4. Test endpoints: `curl http://192.168.1.101/lux`

### Rain sensor shows 0
1. Ensure ArduSafeMon is connected to COM port
2. Check SharedHardware logs for communication errors
3. Verify SafetyMonitor device works independently

### OPIR values show 0
1. Test HTTP endpoints in browser: http://192.168.1.101/lux
2. Check that OPIR sensor firmware is uploaded
3. Verify network connectivity

## Notes
- All switches are **read-only** - you cannot set values
- Data is cached for 5 seconds to reduce polling load
- MaxSwitch returns 6 (0-5) to work around ASCOM client bugs
- HTTP timeout is 5 seconds - sensor will show last value on network issues
