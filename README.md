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

## problems with CH430?
see here: https://forum.arduino.cc/t/a-fatal-esptool-py-error-occurred-cannot-configure-port-something-went-wrong/1225308/7
This appears to be an issue with a driver update that affects those cheap and cheery clones with a CH430 chip for serial.

look for the driver 3.4.2014.8 dated 08/08/20141

## ip configuration
192.168.1.99  == Rain Sensor and weather conditions from OpenWeatherMap
192.168.1.100 == ArduSafeMon_R4wifi_weather/ArduSafeMon_R4wifi - Sky Condition Sensors - /lux, /sky, /ambient
192.168.1.183 == Wombat Weather Station - /temperature, /humidity, /windspeed
192.168.1.148 == CameraWebServer - ESP32cam; many endpts /capture

## MQTT
### Setup
o Go to Mosquitto Downloads and download the Windows installer.
o Add Mosquitto to PATH:
    Open System Properties > Advanced > Environment Variables.
    Under "System variables", find and select Path, then click Edit.
    Click New and add: C:\Program Files\mosquitto
o Start the Broker:
    Open a Command Prompt.
    Run: mosquitto
o The broker will start on port 1883

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
