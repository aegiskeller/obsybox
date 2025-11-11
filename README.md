# obsybox
Codebase for the observatory-in-a-box project

We have the Ardunio Uno and a L298N motor relay. Comms via serial to PC USB.

## Respond to weather
ArdSafeMon is takes input from a ZTS-3000-YUX-R01 rain sensor.

Original write-up: https://www.cloudynights.com/topic/792701-arduino-based-rg-11-safety-monitor-for-nina-64bit/

Link above contains ASCOM driver ArduSafeMon

Wiring diagram for the ZTS-3000-YUX-R01 rain sensor:
![image](https://github.com/user-attachments/assets/9bf2799b-9501-4f02-9be2-b0056b361316)

Power is a 10-30VDC to BRN and BLK. Voltage supply from the microprocessor is supplied to WHT and relay sense is read from GRN.

### set up ArduSafeMon weather details
in Windows task scheduler, create task GetWeatherMQTT.

Program/script: C:\Users\aegis\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe

Arguments: "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ArduSafeMon_R4wifi_weather\getweather_mqtt.py"

Start in: C:\Users\aegis\Documents\obsybox\ArduSafeMon\ArduSafeMon_R4wifi_weather


## problems with CH430?
see here: https://forum.arduino.cc/t/a-fatal-esptool-py-error-occurred-cannot-configure-port-something-went-wrong/1225308/7
This appears to be an issue with a driver update that affects those cheap and cheery clones with a CH430 chip for serial.

look for the driver 3.4.2014.8 dated 08/08/20141

## ip configuration
- 192.168.1.73 == anemometer
- 192.168.1.74 == dewheater
- 192.168.1.99  == Rain Sensor and weather conditions from OpenWeatherMap (these are sourced from the MiniPC via a scheduler task getweather_mqtt)
- 192.168.1.100 == NOT WORKING ArduSafeMon_R4wifi_weather/ArduSafeMon_R4wifi - Sky Condition Sensors - /lux, /sky, /ambient
- 192.168.1.101 == Sky Condition Sensors - /lux, /sky, /ambient
- 192.168.1.102 == P110 Tapo plug - power meter
- 192.168.1.148 == CameraWebServer - ESP32cam; many endpts /capture
- 192.168.1.183 == Wombat Weather Station - /temperature, /humidity, /windspeed

## MQTT
### Setup
- Go to Mosquitto Downloads and download the Windows installer.
- Add Mosquitto to PATH:
    Open System Properties > Advanced > Environment Variables.
    Under "System variables", find and select Path, then click Edit.
    Click New and add: C:\Program Files\mosquitto
- Start the Broker:
    Open a Command Prompt.
    Run: mosquitto
- The broker will start on port 1883

### Test 
Publish a message: mosquitto_pub -h localhost -t test/topic -m "Hello MQTT"
Subscribe to a topic: mosquitto_sub -h localhost -t test/topic

### Configure for local network
edit C:\Program Files\mosquitto\mosquitto.conf
> password_file C:\Program Files\mosquitto\mqtt_pass.txt
> listener 1883 0.0.0.0

run mosquitto broker
>mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v 

and external client:
 mosquitto_sub -h 192.168.1.4 -t opir_sensor

### IOTServer
Work through the following setup:
https://youtu.be/_DO2wHI6JWQ?si=jBXVhuQ4y__hzBQL

This installs IOTstack:
cd IOTStack
./menu.sh

To see the five containers running:

~/IOTstack $ docker-compose ps

NAME           IMAGE                    COMMAND                  SERVICE        CREATED        STATUS                  PORTS

grafana        grafana/grafana          "/run.sh"                grafana        19 hours ago   Up 19 hours (healthy)   0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp

influxdb       influxdb:1.8             "/entrypoint.sh inflâ¦"   influxdb       19 hours ago   Up 19 hours (healthy)   0.0.0.0:8086->8086/tcp, [::]:8086->8086/tcp

mosquitto      iotstack-mosquitto       "/docker-entrypoint.â¦"   mosquitto      19 hours ago   Up 19 hours (healthy)   0.0.0.0:1883->1883/tcp, [::]:1883->1883/tcp

nodered        iotstack-nodered         "./entrypoint.sh"        nodered        19 hours ago   Up 19 hours (healthy)   0.0.0.0:1880->1880/tcp, [::]:1880->1880/tcp

portainer-ce   portainer/portainer-ce   "/portainer"             portainer-ce   19 hours ago   Up 19 hours             0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp, 0.0.0.0:9000->9000/tcp, [::]:9000->9000/tcp, 0.0.0.0:9443->9443/tcp, [::]:9443->9443/tcp

### MQTT Topics

|Topic| Emitting Device| Description|
|-----|----------------|------------|
|obsybox/dewheater| dewheater Wemos D1| {"ambtemp":16.60,"ambhum":45.00,"teltemp":0.00,"dewpt":5.60,"heaterpower":99.00,"deltat":5.00,"mode":"A"}|
|obsybox/weathersafety| ArduSafeMon Ardunino R4 Wifi| {"safe":true,"reason":"All conditions safe (median)"}|
|obsybox/weather| getweather_mqtt.py sched task on miniPC| uses OpenSky API {"temperature": 13.57, "humidity": 44, "weather": "scattered clouds", "wind_speed": 2.92, "clouds": 27, "timestamp": 1750563615.6028142}|
|obsybox/system_monitoring| minipc_sys.py sched task on mini pc; cron job rpiSystem.sh on Pis| {"cpu_temp": 21.1, "cpu_load": 12.0, "disk_free_gb": 67.2, "hostname": "wombat-mini-pc", "wifi_strength": 88}|
|obsybox/anemometer| SparkFun Thing Dev|{"t":nan,"h":nan,"ws":nan}|
|obsybox/opir_sensor|Arduino MKR 1010 Wifi|{"lux":143.56,"sky":11.81,"ambient":17.13,"ir":726,"full":2078,"aht_temp":16.20,"aht_hum":43.27}|
|obsybox/power_usage| Tapo P110 plug from 192.168.1.49 once a minute; on rpis50| ip, power, timestamp|

## NINA Safety Monitor

The `nina_safetymon/` directory contains a comprehensive safety monitoring system for NINA astrophotography software. This system protects expensive observatory equipment by detecting when NINA becomes unresponsive and automatically triggering emergency shutdown procedures.

### Key Features
- **Continuous Monitoring**: Watches NINA process status and log file activity
- **Emergency Shutdown**: Automatically stops telescope, closes dome, and shuts down accessories
- **MQTT Integration**: Uses existing obsybox MQTT infrastructure for alerts and control
- **Weather Integration**: Integrates with ArduSafeMon weather safety monitoring
- **Multiple Detection Methods**: Process monitoring, log analysis, and optional heartbeat integration

### Quick Start
```powershell
cd nina_safetymon
python -m venv venv                                       # Create virtual environment
.\venv\Scripts\python.exe -m pip install -r requirements.txt  # Install dependencies
.\venv\Scripts\python.exe setup.py                       # Verify setup
.\venv\Scripts\python.exe nina_safety_monitor.py         # Test run
install_safety_service.bat                               # Install as service (run as Admin)
```

### Safety Actions
When NINA becomes unresponsive, the system automatically:
1. Stops telescope tracking and aborts slews via ASCOM
2. Closes dome/roof using ASCOM drivers  
3. Shuts down dew heaters and accessories via MQTT
4. Terminates NINA process if still running
5. Logs all actions and sends MQTT alerts

See `nina_safetymon/README.md` for detailed setup and configuration instructions.

## Windows deployment (quick)

We include helper files to deploy `get_system_stats.py` on Windows using Task Scheduler.

-- Wrapper (created in repo): `systemMonitoring/ComputeMonitoring/run_get_system_stats.cmd` — runs the Python script and appends stdout/stderr to `C:\Logs\obsybox\get_system_stats.log`.
-- Deploy helper: `systemMonitoring/ComputeMonitoring/deploy_task.ps1` — writes/updates the wrapper and registers a scheduled task that runs every minute.

Quick steps (run PowerShell as Administrator):

1. Generate the wrapper and register the task (uses Python on PATH unless you provide -PythonPath):

    .\systemMonitoring\ComputeMonitoring\deploy_task.ps1 -PythonPath 'C:\Path\To\python.exe'

2. Start the task now (optional):

    schtasks /Run /TN "Obsybox_GetSystemStats"

3. Tail the log:

    Get-Content C:\Logs\obsybox\get_system_stats.log -Tail 200 -Wait

If you prefer the raw `schtasks` command, example (PowerShell quoting):

    schtasks /Create /SC MINUTE /MO 1 /TN "Obsybox_GetSystemStats" /TR 'C:\Users\Admin\Documents\Arduino\obsybox\systemMonitoring\ComputeMonitoring\run_get_system_stats.cmd' /RL HIGHEST /F /RU "SYSTEM"

See `readme_windows_deploy` in the repo for a full explanation, troubleshooting tips and alternatives (Register-ScheduledTask, non-minute sampling, service options).

Undeploy example
-----------------
To remove the task and wrapper, run the undeploy helper from the repo root as Administrator:

    .\systemMonitoring\ComputeMonitoring\undeploy_task.ps1

To also remove the log file:

    .\systemMonitoring\ComputeMonitoring\undeploy_task.ps1 -RemoveLog

You can also remove the task directly with schtasks if you prefer:

    schtasks /Delete /TN "Obsybox_GetSystemStats" /F


