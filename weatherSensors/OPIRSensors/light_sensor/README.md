# TSL2591 Light Sensor with WiFi and MQTT

Standalone light sensor module using TSL2591 high-dynamic-range light sensor with MQTT integration for the obsybox observatory network.

## Features

- High dynamic range light sensing (188 μLux to 88,000 Lux)
- Separate infrared and visible light measurements
- Full spectrum light measurement
- Calculated lux value for illuminance
- WiFi connectivity with static IP
- MQTT publishing to `obsybox/light_sensor`
- Read-then-transmit strategy to avoid WiFi/I2C interference
- 10-second update interval

## Hardware Connections

| TSL2591 Pin | ESP8266 Pin | GPIO |
|-------------|-------------|------|
| VIN         | 3.3V        | -    |
| GND         | GND         | -    |
| SCL         | D1          | GPIO5|
| SDA         | D2          | GPIO4|

**Important**: TSL2591 requires 3.3V power (NOT 5V)

## Required Libraries

Install via Arduino IDE Library Manager:

1. **Adafruit TSL2591** - Light sensor driver
   - Search for "Adafruit TSL2591"
   - Install "Adafruit TSL2591 Library" by Adafruit
   - Also install "Adafruit Unified Sensor" if prompted

2. **PubSubClient** - MQTT client
   - Search for "PubSubClient"
   - Install "PubSubClient" by Nick O'Leary

3. **ESP8266WiFi** - Built-in with ESP8266 board package

## Configuration

Before uploading, edit `arduino_secrets.h` with your network credentials:

```cpp
#define SECRET_SSID "your_wifi_ssid"
#define SECRET_PASS "your_wifi_password"

#define MQTT_SERVER "192.168.1.49"  // Your MQTT broker IP
#define MQTT_USER ""                 // MQTT username (or empty)
#define MQTT_PASS ""                 // MQTT password (or empty)

#define STATIC_IP 192, 168, 1, 103   // Adjust to your network
#define GATEWAY_IP 192, 168, 1, 1
```

**Important**: The `arduino_secrets.h` file is git-ignored to protect your credentials.

## Board Setup

1. **Board**: Select **LOLIN(WEMOS) D1 R2 & mini**
   - Go to **Tools** → **Board** → **ESP8266 Boards** → **LOLIN(WEMOS) D1 R2 & mini**
2. **Upload Speed**: 115200 (or 921600 for faster uploads)
3. **CPU Frequency**: 80 MHz (default)
4. **Flash Size**: 4MB (FS:2MB OTA:~1019KB)

## Upload Instructions

Using Arduino CLI (from project root):
```powershell
.\bin\arduino-cli compile --fqbn esp8266:esp8266:d1_mini weatherSensors\OPIRSensors\light_sensor
.\bin\arduino-cli upload --fqbn esp8266:esp8266:d1_mini --port COM[X] weatherSensors\OPIRSensors\light_sensor
```

Replace `COM[X]` with your actual COM port.

## Serial Monitor

- **Baud Rate**: 115200
- **Line Ending**: Newline or Both NL & CR

## Output Format

### Serial Output
Light readings are published every 10 seconds:
```
Reading sensor...
Lux: 1234 | IR: 567 | Visible: 890 | Full: 1457
Published: {"Lux":1234,"Infrared":567,"Visible":890,"Full":1457}
```

### MQTT Topic
- **Topic**: `obsybox/light_sensor`
- **Format**: JSON
- **Payload**: `{"Lux":1234,"Infrared":567,"Visible":890,"Full":1457}`
- **Frequency**: Every 10 seconds

### Field Descriptions
- **Lux**: Calculated illuminance in lux (brightness for human eye)
- **Infrared**: Infrared light level (raw count, 0-65535)
- **Visible**: Visible light level (Full - Infrared)
- **Full**: Full spectrum light level (raw count, 0-65535)

## Sensor Configuration

Default configuration (can be adjusted in `configureSensor()`):

- **Gain**: 25x (Medium) - Good for general outdoor use
- **Integration Time**: 100ms - Balance of speed and sensitivity

### Adjusting Gain

If readings are saturated (65535) or too low (0), adjust gain:

```cpp
// In configureSensor() function:
tsl.setGain(TSL2591_GAIN_LOW);   // 1x - bright daylight
tsl.setGain(TSL2591_GAIN_MED);   // 25x - normal conditions (default)
tsl.setGain(TSL2591_GAIN_HIGH);  // 428x - dim conditions
tsl.setGain(TSL2591_GAIN_MAX);   // 9876x - very dim/night
```

### Adjusting Integration Time

```cpp
tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);  // Default
tsl.setTiming(TSL2591_INTEGRATIONTIME_200MS);  // More sensitive
tsl.setTiming(TSL2591_INTEGRATIONTIME_300MS);  // Even more sensitive
```

## Applications

### Sky Brightness Monitoring
- Track sky brightness for observing conditions
- Detect light pollution levels
- Monitor dawn/dusk transitions
- Correlate with seeing conditions

### Weather Observations
- Cloud detection (combined with IR temperature sensor)
- Daylight monitoring
- Automatic dome/roof control based on light levels

### Data Analysis
- **Infrared vs Visible ratio** can indicate atmospheric conditions
- **Lux trends** show twilight progression
- **Full spectrum** useful for calibration

## Troubleshooting

### Sensor Not Found

If TSL2591 initialization fails:

1. **Run I2C scanner** (use the one from `opir_sensor/i2c_scanner`)
2. **Check wiring** - especially SCL and SDA connections
3. **Verify I2C address**: TSL2591 should appear at 0x29
4. **Check power**: Ensure stable 3.3V supply (NOT 5V!)

### Readings Always 0 or 65535

- **0**: Too dark, or sensor covered → Increase gain
- **65535**: Saturated, too bright → Decrease gain or integration time
- Try adjusting gain settings in `configureSensor()`

### WiFi Interference

The read-then-transmit strategy minimizes this, but if you still see issues:
- Add a 100-470µF capacitor across ESP8266 power pins
- Use external power supply (not just USB)

## Integration with obsybox Network

### MQTT Monitoring
Monitor the sensor data from any MQTT client:
```powershell
mosquitto_sub -h 192.168.1.49 -t obsybox/light_sensor
```

### Grafana Integration
To visualize in Grafana/InfluxDB:
1. Configure InfluxDB to subscribe to `obsybox/light_sensor`
2. Parse JSON payload to extract fields
3. Create dashboard panels for:
   - Lux trend (sky brightness)
   - IR/Visible ratio
   - Full spectrum readings

### Node-RED Integration
Add MQTT input node subscribing to `obsybox/light_sensor`:
- Trigger observatory operations based on light levels
- Detect sunrise/sunset for automated schedules
- Combine with other weather sensors for safety decisions

### Combining with IR Temperature Sensor

When used alongside the IR temperature sensor (192.168.1.102):
- Subscribe to both `obsybox/ir_sensor` AND `obsybox/light_sensor`
- Correlate sky temperature with light levels for cloud detection
- Use both for comprehensive observing condition assessment

## Device Network Configuration

Add to your obsybox network documentation:
- **Device**: Light Sensor (TSL2591)
- **IP**: 192.168.1.103
- **MQTT Topic**: `obsybox/light_sensor`
- **Hardware**: Lolin ESP8266 + TSL2591

## References

- [TSL2591 Datasheet](https://ams.com/tsl25911)
- [Adafruit TSL2591 Library](https://github.com/adafruit/Adafruit_TSL2591_Library)
- [Light Pollution Measurement](https://www.lightpollutionmap.info)
