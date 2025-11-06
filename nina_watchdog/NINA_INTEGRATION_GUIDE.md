# NINA Safety Monitor Integration Guide

## Overview
The NINA Safety Monitor is a comprehensive safety system that integrates with N.I.N.A. (Nighttime Imaging 'N' Astronomy) software to provide real-time monitoring of weather conditions, equipment status, and automatic emergency shutdown capabilities.

## Features
- **Real-time Weather Monitoring**: Monitors obsybox MQTT network for weather safety status
- **ASCOM Integration**: Controls telescope and dome through ASCOM drivers
- **Emergency Shutdown**: Automatic parking of telescope and dome closure during unsafe conditions
- **NINA Process Monitoring**: Detects if NINA is running and adjusts monitoring accordingly
- **System Tray Icon**: Minimizes to system tray with status indicators
- **Configurable Safety Parameters**: Customizable timeouts and safety thresholds

## NINA Integration Methods

### Method 1: External Script Integration (Recommended)
1. In NINA, go to **Tools** > **External Scripts**
2. Add a new script with the following settings:
   - **Name**: "NINA Watchdog Safety Monitor"
   - **Path**: `C:\Users\aegis\Documents\obsybox\nina_watchdog\nina_watchdog_script.bat`
   - **Arguments**: (leave blank)
   - **Working Directory**: (leave blank - script uses absolute paths)

### Method 2: Manual Launch
1. Navigate to `C:\Users\aegis\Documents\obsybox\nina_watchdog\`
2. Double-click `nina_watchdog_script.bat`
3. The GUI will open and minimize to system tray

### Method 3: PowerShell Launch
```powershell
C:\Users\aegis\Documents\obsybox\nina_safetymon\launch_safety_gui_absolute.ps1
```

## GUI Features

### Main Controls
- **Start Monitoring**: Begins continuous safety monitoring
- **Stop Monitoring**: Stops the monitoring loop
- **Emergency Shutdown**: Immediately executes emergency shutdown sequence
- **Refresh Status**: Updates equipment connection status

### Status Display
- **MQTT Connection**: Shows connection to obsybox weather network
- **Telescope Status**: Displays ASCOM telescope connection and position
- **Dome Status**: Shows ASCOM dome connection and state
- **NINA Process**: Indicates if NINA is currently running
- **Weather Safety**: Real-time weather safety status from sensors

### Configuration Panel
- **Monitoring Interval**: How often to check safety conditions (default: 30 seconds)
- **Emergency Timeout**: Maximum time for emergency shutdown sequence (default: 15 minutes)
- **Auto-minimize**: Automatically minimize to system tray on startup

## Safety Sequence

When unsafe conditions are detected, the monitor executes this sequence:

1. **Telescope Safety**:
   - Abort any active slewing
   - Stop tracking
   - **MANDATORY PARK** (will retry until successful)
   - Verify telescope is at park position

2. **Dome Safety**:
   - Close dome (only after telescope is safely parked)
   - Verify dome is closed

3. **Equipment Monitoring**:
   - Continue monitoring for condition changes
   - Log all actions with timestamps

## Configuration

### ASCOM Drivers
The system uses these ASCOM drivers (auto-detected):
- **Telescope**: `ASCOM.GS.Sky.Telescope`
- **Dome**: `ASCOM.RRCI.Dome`

### MQTT Settings
- **Broker**: `192.168.1.49:1883`
- **Topics**:
  - `obsybox/weathersafety` - Safety status from ArduSafeMon
  - `obsybox/weather` - OpenWeatherMap data
  - `obsybox/dewheater` - Dew heater telemetry

### Configuration File
Settings are stored in `nina_safety_config.json`:
```json
{
    "ascom": {
        "telescope_driver": "ASCOM.GS.Sky.Telescope",
        "dome_driver": "ASCOM.RRCI.Dome"
    },
    "safety": {
        "emergency_timeout_minutes": 15,
        "monitoring_interval_seconds": 30,
        "require_telescope_park": true
    },
    "mqtt": {
        "broker": "192.168.1.49",
        "port": 1883,
        "topics": {
            "weather_safety": "obsybox/weathersafety",
            "weather": "obsybox/weather"
        }
    }
}
```

## Logging

The system maintains detailed logs:
- **GUI Log**: `nina_safety_gui.log` - GUI events and user actions
- **Monitor Log**: `nina_safety_monitor.log` - Background monitoring events
- **Emergency Log**: `emergency_shutdown.log` - Emergency sequence details

## Troubleshooting

### Common Issues

1. **"ASCOM driver not found"**
   - Ensure ASCOM Platform is installed
   - Run `detect_ascom_drivers.py` to verify available drivers
   - Check that telescope/dome hardware is connected

2. **"MQTT connection failed"**
   - Verify obsybox MQTT broker is running at 192.168.1.49
   - Check network connectivity
   - Ensure broker allows anonymous connections

3. **"GUI won't start"**
   - Verify Python virtual environment is set up correctly
   - Run launcher script from command line to see error messages
   - Check that all dependencies are installed

4. **"Emergency shutdown failed"**
   - Check ASCOM connections
   - Verify telescope is not physically obstructed
   - Review emergency_shutdown.log for detailed error messages

### Testing Commands

Test ASCOM telescope connection:
```bash
.\venv\Scripts\python.exe test_ascom_telescope.py
```

Test ASCOM dome connection:
```bash
.\venv\Scripts\python.exe test_ascom_dome.py
```

Test MQTT connectivity:
```bash
.\venv\Scripts\python.exe -c "import paho.mqtt.client as mqtt; print('MQTT library working')"
```

## Safety Notes

⚠️ **CRITICAL**: The telescope MUST park before the dome closes to prevent collision damage.

⚠️ **IMPORTANT**: Always test the emergency shutdown sequence during daylight hours before using for actual observations.

⚠️ **NETWORK**: The system requires network connectivity to the obsybox MQTT broker for weather monitoring.

## Support

For issues or questions:
1. Check log files for error details
2. Run diagnostic scripts to test individual components
3. Verify ASCOM driver installations and connectivity
4. Test MQTT broker connectivity and topics

## Version Information
- **GUI Application**: `simple_safety_gui.py`
- **Background Monitor**: `nina_safety_monitor.py`
- **Emergency Handler**: `emergency_shutdown.py`
- **Configuration**: `nina_safety_config.json`
- **Python Environment**: Virtual environment with exact dependency pinning