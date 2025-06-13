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