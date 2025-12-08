# obsybox - Observatory-in-a-Box Codebase Guide

## Project Overview
Automated observatory control system integrating Arduino-based sensors, Python automation scripts, and ASCOM telescope control. Core mission: enable autonomous astronomical observations with weather monitoring, target scheduling, and hardware control.

## Architecture & Communication

### MQTT-Based Sensor Network
All hardware communicates via MQTT broker (`192.168.1.49:1883`). Topics follow `obsybox/<component>` pattern:
- `obsybox/weather` - OpenWeatherMap data from scheduled PC task
- `obsybox/weathersafety` - Safety status from ArduSafeMon (`{"safe":true,"reason":"..."}`)
- `obsybox/dewheater` - Dew heater telemetry (WeMos D1)
- `obsybox/power_usage` - Tapo P110 power monitoring

**Critical**: Devices use static IPs (see README.md). Arduino devices include MQTT client code with secrets in `arduino_secrets.h`.

### Hardware Components
1. **ArduSafeMon (Arduino R4 WiFi, IP .99)**: Rain sensor + weather safety logic, publishes safety status
2. **Dew Heater (WeMos D1, IP .74)**: I2C master-slave, auto dew point control, web interface
3. **Sky Sensors (Arduino R4, IP .101)**: `/lux`, `/sky`, `/ambient` endpoints
4. **Anemometer (IP .73)**: Wind speed monitoring
5. **Wombat Weather Station (IP .183)**: `/temperature`, `/humidity`, `/windspeed`
6. **ESP32-CAM (IP .148)**: AllSky monitoring, `/capture` endpoint

## Key Development Workflows

### Arduino Device Development
```powershell
# Arduino CLI is in bin/arduino-cli (not in PATH)
.\bin\arduino-cli compile --fqbn arduino:renesas_uno:unor4wifi ArduSafeMon/ArduSafeMon_R4wifi_weather/ArduSafeMon_R4wifi
.\bin\arduino-cli upload --fqbn arduino:renesas_uno:unor4wifi --port COM3 <sketch_path>
```

**Common issue**: CH430 clone chip driver problems. Need driver version 3.4.2014.8 (dated 08/08/2014).

### NINA Target Scheduling (`nina_scheduling/`)
**Primary tool**: `target_selector_gui.py` (GUI) or `findTargets.py` (CLI)

Workflow:
1. Scrapes eclipsing binary minima from var.astro.cz
2. Filters by altitude, azimuth, magnitude, declination
3. Generates NINA sequence JSON files from templates (`*.template.json` pattern)
4. Tracks scheduled/observed targets in SQLite database (`schema.sql`)

**Database pattern**: Uses astronomical dating (noon-to-noon), links sequences → scheduled_targets → observations with photometry tracking.

```powershell
# Setup virtual environment (REQUIRED to avoid numpy/astropy conflicts)
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Run GUI (preferred)
python target_selector_gui.py

# Import observation logs post-session
# Use logexploit from the logexploit directory with shared database
cd logexploit
python -m logexploit --db ..\nina_scheduling\observations.sqlite path\to\nina-log.log
```

**Key configuration** in `findTargets.py`:
- `OBSERVER_LOCATION`: Observatory lat/lon/elevation
- `MIN_ALTITUDE`, `MAX_ALTITUDE`: Elevation constraints (30°-85°)
- `ALLOWED_AZIMUTHS`: Direction limits (avoid obstructions)
- `NINA_TEMPLATE_FILE`: Base JSON for sequence generation

### ASCOM Telescope Control (`ascom_api/`)
Uses `win32com.client` + `pythoncom` for ASCOM driver integration. See `telescope_control.py`:
- `DomeController`: Roll-off roof control (RRCI driver)
- `TelescopeController`: Mount slewing, tracking
- `CameraController`: Imaging, cooling, dark frame capture

Configuration in `telescope_config.ini` with safety limits (sun altitude, wind speed, slew distance).

### Weather Safety Windows Task
Windows Task Scheduler runs `getweather_mqtt.py` every 2-10 minutes:
```
Program: C:\Users\aegis\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe
Arguments: "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ArduSafeMon_R4wifi_weather\getweather_mqtt.py"
Start in: C:\Users\aegis\Documents\obsybox\ArduSafeMon\ArduSafeMon_R4wifi_weather
```

## Project-Specific Conventions

### File Organization Patterns
- Arduino sketches: `<component>/version<N>/<device_name>/<device_name>.ino`
- Active versions in numbered dirs (e.g., `dewHeater/version3/`)
- Secrets management: `arduino_secrets.h`, `secrets.py`, `weather_secrets.py` (git-ignored)
- MQTT credentials: `mqtt_pass.txt` (see Mosquitto config)

### Python Environment
- **Always use venv** for `nina_scheduling/` (astropy/numpy version conflicts)
- Root `requirements.txt`: Core deps (Flask, tapo, requests)
- Subproject requirements: `nina_scheduling/requirements.txt` (selenium, astropy, astroquery)

### Arduino Code Patterns
- Static IP configuration in `setup()` with `WiFi.config()`
- MQTT reconnect logic with exponential backoff
- Watchdog timers for reliability (`WDT.begin(8000)` on R4 WiFi)
- EEPROM for persistent config (weather thresholds, calibration)
- Web interfaces on port 80 with live refresh (`<meta http-equiv="refresh" content="30">`)

### Database Conventions (`nina_scheduling/`)
- Astronomical nights: Date reflects noon-to-noon observing session
- Sequences are reusable across nights via `scheduled_targets` junction table
- Log imports match timestamps to scheduled targets for completion tracking
- Use `observation_db.py` helper functions, never raw SQL

## External Dependencies
- **ASCOM Platform**: Required for telescope control on Windows
- **RRCI Driver**: Rolling roof control (https://projecthub.arduino.cc/cfar/rolling-roof-computer-interface-rrci-a7f9ac)
- **NINA**: Nighttime Imaging 'N' Astronomy software (consumes generated JSON sequences)
- **Mosquitto MQTT Broker**: Install to `C:\Program Files\mosquitto`, configure with `mqtt_pass.txt` and listener `0.0.0.0:1883`
- **IOTstack**: Docker stack with Grafana, InfluxDB, Node-RED, Portainer (for data visualization)

## Testing & Debugging
- Arduino: Serial monitor at 9600 baud for debug output
- MQTT: `mosquitto_sub -h 192.168.1.49 -t obsybox/#` to monitor all topics
- Web interfaces: Navigate to static IPs (see README) to verify device status
- NINA sequences: Import JSON to NINA and validate via "Sequence > Validate"

## Common Gotchas
1. **Virtual environment**: Always activate before running `nina_scheduling` scripts
2. **Static IPs**: Device IPs are hardcoded; DHCP changes break MQTT communication
3. **NINA templates**: Must exist in working directory or specify full path
4. **Windows paths**: Use raw strings or forward slashes in Python (`Path` objects preferred)
5. **ASCOM threading**: Must call `pythoncom.CoInitialize()` before COM operations in threads
6. **Serial port reconnection**: NINA/ASCOM can hold serial ports after disconnect. Arduino code includes:
   - Periodic `Serial.flush()` to prevent buffer buildup
   - Connection detection and auto-reinitialization on reconnect
   - Activity-based monitoring to detect disconnection
   - If problems persist, use USB Device Tree Viewer to manually reset the port
