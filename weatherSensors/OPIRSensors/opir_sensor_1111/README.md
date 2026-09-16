# OPIR Sensor - Combined IR Temperature + Light Sensor

Combined sensor system using MLX90614 IR temperature sensor and TSL2591 light sensor with MQTT integration for the obsybox observatory network.

## Features

- **MLX90614 IR Temperature Sensor**
  - Non-contact IR temperature sensing
  - Ambient temperature measurement
  - Sky temperature measurement (for cloud detection)

- **TSL2591 Light Sensor**
  - High dynamic range light sensing
  - Lux calculation
  - Infrared, visible, and full spectrum readings

- **MQTT Integration**
  - Topic: `obsybox/opir_sensor`
  - JSON payload with all sensor readings
  - 10-second update interval

## Hardware Connections

Both sensors share the same I2C bus:

| Component | Pin | ESP8266 |
|-----------|-----|---------|
| MLX90614 VIN | VIN | 3.3V |
| MLX90614 GND | GND | GND |
| MLX90614 SCL | SCL | D1 (GPIO5) |
| MLX90614 SDA | SDA | D2 (GPIO4) |
| TSL2591 VIN | VIN | 3.3V |
| TSL2591 GND | GND | GND |
| TSL2591 SCL | SCL | D1 (GPIO5) |
| TSL2591 SDA | SDA | D2 (GPIO4) |

**Note**: Both sensors use the same I2C bus. They have different I2C addresses:
- MLX90614: 0x5A
- TSL2591: 0x29

## Required Libraries

Install via Arduino IDE Library Manager:

1. **Adafruit MLX90614** - IR temperature sensor
2. **Adafruit TSL2591** - Light sensor
3. **PubSubClient** - MQTT client
4. **ESP8266WiFi** - Built-in with ESP8266 board package

## Configuration

Edit `arduino_secrets.h` with your network credentials:

```cpp
#define SECRET_SSID "your_wifi_ssid"
#define SECRET_PASS "your_wifi_password"

#define MQTT_SERVER "192.168.1.49"  // Your MQTT broker IP
#define STATIC_IP 192, 168, 1, 103   // Adjust to your network
```

## MQTT Payload

**Topic**: `obsybox/opir_sensor`

**Format**: JSON

```json
{
  "AmbientTemp": 23.45,
  "SkyTemp": 15.67,
  "Lux": 1234,
  "Infrared": 567,
  "Visible": 890,
  "Full": 1457
}
```

### Field Descriptions

- **AmbientTemp** (°C): Temperature of the sensor itself (ambient air)
- **SkyTemp** (°C): Temperature of the sky being measured (IR reading)
- **Lux**: Calculated illuminance in lux
- **Infrared**: Infrared light level (raw count)
- **Visible**: Visible light level (Full - Infrared)
- **Full**: Full spectrum light level (raw count)

## Upload Instructions

Using Arduino CLI (from project root):
```powershell
.\bin\arduino-cli compile --fqbn esp8266:esp8266:d1_mini weatherSensors\OPIRSensors\opir_sensor
.\bin\arduino-cli upload --fqbn esp8266:esp8266:d1_mini --port COM[X] weatherSensors\OPIRSensors\opir_sensor
```

Or using Arduino IDE:
1. Open `opir_sensor.ino`
2. Select board: **LOLIN(WEMOS) D1 R2 & mini**
3. Select correct COM port
4. Click Upload

## Serial Monitor Output

Baud Rate: **115200**

```
=== OPIR Sensor - IR Temp + Light ===
Device: OPIR_Sensor
======================================
Initializing I2C bus...
Initializing MLX90614 (IR Temp)...OK!
Initializing TSL2591 (Light)...OK!
TSL2591 Configuration:
  Gain: 25x (Med)
  Integration: 100 ms
Connecting to WiFi........
WiFi connected!
IP: 192.168.1.103
RSSI: -45 dBm

Setup complete!
Reading sensors every 10 seconds...
======================================

--- Reading Sensors ---
Temperature - Ambient: 23.45 °C, Sky: 15.67 °C
Light - Lux: 1234, IR: 567, Visible: 890, Full: 1457
Published: {"AmbientTemp":23.45,"SkyTemp":15.67,"Lux":1234,"Infrared":567,"Visible":890,"Full":1457}
======================================
```

## Applications

### Cloud Detection
Sky temperature significantly lower than ambient indicates clear skies. Smaller difference suggests cloud cover.

```
Clear sky: SkyTemp << AmbientTemp (e.g., -10°C difference)
Cloudy: SkyTemp ≈ AmbientTemp (e.g., -2°C difference)
```

### Light Level Monitoring
- Monitor sky brightness for observing conditions
- Detect dawn/dusk transitions
- Light pollution assessment

## Troubleshooting

### Sensor Not Found

If MLX90614 or TSL2591 initialization fails:

1. **Run I2C scanner** (from `ir_sensor/i2c_scanner` folder)
2. **Check wiring** - especially SCL and SDA connections
3. **Verify I2C addresses**:
   - MLX90614 should appear at 0x5A
   - TSL2591 should appear at 0x29
4. **Check power** - ensure stable 3.3V supply

### Invalid Temperature Readings

If ambient temperature shows ~1000°C or other invalid values:
- This is a **power supply issue** with WiFi interference
- The sketch uses read-then-transmit strategy to minimize this
- Consider adding a capacitor (100-470µF) across power pins
- Double-read of ambient temperature helps with stability

### Light Sensor Saturation

If readings are maxed out or zero:
- Adjust TSL2591 gain in `configureLightSensor()`:
  - `TSL2591_GAIN_LOW` (1x) - bright conditions
  - `TSL2591_GAIN_MED` (25x) - normal conditions (default)
  - `TSL2591_GAIN_HIGH` (428x) - dim conditions
  - `TSL2591_GAIN_MAX` (9876x) - very dim conditions

## Integration with obsybox Network

### MQTT Monitoring
```powershell
mosquitto_sub -h 192.168.1.49 -t obsybox/opir_sensor
```

### Grafana Dashboard
Create panels for:
- Sky temperature trend (cloud cover indicator)
- Ambient temperature monitoring
- Sky brightness (Lux)
- Sky condition derived from temp differential

### Node-RED Automation
Use for weather safety decisions:
- Combine sky temp with other weather data
- Trigger observatory closure on cloudy conditions
- Monitor light pollution levels

## References

- [MLX90614 Datasheet](https://www.melexis.com/en/product/MLX90614/Digital-Plug-Play-Infrared-Thermometer-TO-Can)
- [TSL2591 Datasheet](https://ams.com/tsl25911)
- [Cloud Detection with IR Sensors](https://www.deekayen.net/projects/weather-station/cloud-sensor)
