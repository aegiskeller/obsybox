# ObsyBox Relay Controller

Arduino-based relay switch controller for observatory automation with ASCOM driver interface.

## Overview

The ObsyBox Relay Controller provides WiFi-enabled control of up to 4 relay channels for switching observatory equipment on/off remotely. It integrates seamlessly with NINA and ASCOM-compatible software for automated observations.

## Hardware Requirements

- **NodeMCU ESP8266** (WiFi-enabled development board)
- **4-Channel Relay Module** (5V, active low recommended)
- **Jumper wires** for connections

### Wiring Diagram

```
NodeMCU ESP8266      †    4-Channel Relay Module
Pin D1               †    Relay 1 (Mount)
Pin D2               †    Relay 2 (Camera)
Pin D3               †    Relay 3 (Focuser)  
Pin D4               †    Relay 4 (Aux)
3V3                  †    VCC (if 3.3V relay) OR 5V † VCC (if 5V relay)
GND                  †    GND
```

**Note**: Most relay modules are **active LOW**, meaning a LOW signal turns the relay ON. The code handles this automatically with the `relayInvert` setting.

## Features

### Arduino Firmware
-  WiFi connectivity with static IP assignment
-  MQTT integration for status reporting
-  Web interface for manual control
-  RESTful API for programmatic access
-  EEPROM storage for persistent relay states
-  Watchdog timer for reliability
-  Status LED indication
-  JSON-based communication

### Python Driver
-  ASCOM-compatible switch interface
-  Automatic device discovery
-  Error handling and retry logic
-  Status monitoring and logging
-  Performance optimization

### NINA Integration
-  Compatible with NINA's switch interface
-  Schedulable equipment control
-  Safety interlocks and emergency stop

## Quick Start

### 1. Arduino Setup

1. Install required libraries in Arduino IDE:
   ```
   ESP8266WiFi (ESP8266 Core library)
   MQTT by Joel Gaehwiler  
   ArduinoJson by Benoit Blanchon
   ESP8266WebServer (ESP8266 Core library)
   ```

2. Copy `arduino_secrets.h` to your sketch folder and update WiFi credentials:
   ```cpp
   #define SECRET_SSID "YourWiFiNetwork"
   #define SECRET_PASS "YourWiFiPassword"
   ```

3. Upload `RelayController.ino` to your NodeMCU ESP8266

4. Open Serial Monitor (9600 baud) to verify connection and get IP address

### 2. Python Environment

```bash
# Install Python dependencies
pip install -r requirements.txt

# Test connectivity
python test_relay_controller.py
```

### 3. Verify Operation

1. **Web Interface**: Navigate to `http://192.168.1.76` (or your device IP)
2. **API Test**: `curl http://192.168.1.76/status`
3. **Switch Control**: `curl -X POST http://192.168.1.76/relay/1/on`

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web interface |
| GET | `/status` | Device and relay status (JSON) |
| GET | `/relay/{1-4}` | Individual relay status |
| POST | `/relay/{1-4}/on` | Turn relay on |
| POST | `/relay/{1-4}/off` | Turn relay off |
| POST | `/relay/{1-4}/toggle` | Toggle relay state |
| GET | `/ascom/status` | ASCOM-compatible status |
| POST | `/ascom/setswitch` | ASCOM switch control |

### Example API Responses

**Device Status** (`GET /status`):
```json
{
  "device": "ObsySwitch",
  "firmware": "1.0.0",
  "uptime": 123456,
  "ip": "192.168.1.76",
  "relays": [
    {"id": 1, "name": "Mount", "state": false, "pin": 2},
    {"id": 2, "name": "Camera", "state": true, "pin": 3},
    {"id": 3, "name": "Focuser", "state": false, "pin": 4},
    {"id": 4, "name": "Aux", "state": false, "pin": 5}
  ]
}
```

**Individual Relay** (`GET /relay/1`):
```json
{
  "relay_id": 1,
  "name": "Mount",
  "state": false,
  "pin": 2
}
```

### Python Usage

```python
from obsyswitch_driver import ObsySwitchController

# Connect to relay controller
controller = ObsySwitchController("192.168.1.76")
controller.connect()

# Control individual relays (0-based indexing)
controller.set_switch(0, True)   # Turn on Mount (relay 1)
controller.set_switch(1, False)  # Turn off Camera (relay 2)

# Check status
mount_on = controller.get_switch(0)
all_states = controller.get_all_switches()

# Emergency stop (turns off all relays)
controller.emergency_stop()

controller.disconnect()
```

### ASCOM Interface

```python
from obsyswitch_driver import ASCOMSwitchV2

# ASCOM-compatible interface
ascom = ASCOMSwitchV2("192.168.1.76")
ascom.Connected = True

# ASCOM standard methods
max_switches = ascom.MaxSwitch
switch_name = ascom.GetSwitchName(0)
switch_state = ascom.GetSwitch(0)
ascom.SetSwitch(0, True)

ascom.Connected = False
```

## NINA Integration

### Setup Steps

1. Install a generic ASCOM Switch driver (if not already available)
2. Configure the driver to use HTTP/REST interface
3. Point the driver to your Arduino's IP address
4. Add switch control to your NINA sequences

### Example NINA Sequence Actions

```json
{
  "action": "SwitchControl",
  "switch_id": 0,
  "switch_name": "Mount",
  "action": "on",
  "condition": "before_sequence"
},
{
  "action": "SwitchControl", 
  "switch_id": 1,
  "switch_name": "Camera",
  "action": "on",
  "condition": "before_imaging"
},
{
  "action": "SwitchControl",
  "switch_id": 0,
  "switch_name": "Mount", 
  "action": "off",
  "condition": "after_sequence"
}
```

## MQTT Integration

The controller publishes status to `obsybox/relays/status` and listens for commands on `obsybox/relays/command`.

**Status Message**:
```json
{
  "device": "ObsySwitch",
  "uptime": 123456,
  "relays": [
    {"id": 1, "name": "Mount", "state": false},
    {"id": 2, "name": "Camera", "state": true}
  ]
}
```

**Command Message**:
```json
{"relay": 1, "action": "on"}
{"relay": 2, "action": "off"}
{"relay": 3, "action": "toggle"}
```

## Configuration

### Static IP Assignment

Update in `RelayController.ino`:
```cpp
IPAddress local_IP(192, 168, 1, 75);  // Change this IP
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
```

### Relay Names and Pins

Customize in `RelayController.ino`:
```cpp
const String relayNames[NUM_RELAYS] = {"Mount", "Camera", "Focuser", "Aux"};
const int relayPins[NUM_RELAYS] = {2, 3, 4, 5};
```

### MQTT Broker

Update in `RelayController.ino`:
```cpp
const char* mqtt_broker = "192.168.1.49";  // Your MQTT broker IP
```

## Troubleshooting

### Common Issues

**Cannot connect to device**:
- Check Arduino is powered and WiFi connected
- Verify IP address in configuration
- Check firewall settings
- Use ping to test network connectivity

**Relays not switching**:
- Verify wiring connections
- Check relay module power supply (5V)
- Test with multimeter on relay outputs
- Check `relayInvert` setting for active low/high

**Slow response times**:
- Check WiFi signal strength (RSSI)
- Verify network congestion
- Consider reducing MQTT publish interval
- Check for interference

### Debug Mode

Enable detailed logging in Python:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View Arduino serial output:
```bash
# macOS/Linux
screen /dev/cu.usbserial-* 9600

# Windows  
# Use Arduino IDE Serial Monitor
```

### Network Diagnostics

```bash
# Test network connectivity
ping 192.168.1.76

# Test web interface
curl -v http://192.168.1.76/status

# Test relay control
curl -X POST http://192.168.1.76/relay/1/on
curl -X POST http://192.168.1.76/relay/1/off
```

## Safety Considerations

 **Important Safety Notes**:

- Use appropriate fuses/circuit breakers for connected equipment
- Ensure relay ratings exceed load requirements  
- Implement software safety interlocks in NINA sequences
- Test emergency stop functionality before deployment
- Keep relay module and Arduino in weatherproof enclosure
- Use proper electrical isolation for high-voltage equipment

## Development

### Building and Testing

```bash
# Run comprehensive tests
python test_relay_controller.py

# Test specific functionality
python -c "from obsyswitch_driver import *; test_relay_controller()"

# Monitor MQTT messages
mosquitto_sub -h 192.168.1.49 -t obsybox/relays/#
```

### Extending Functionality

To add more relays:
1. Update `NUM_RELAYS` constant in Arduino code
2. Add pins to `relayPins[]` array
3. Update relay names in `relayNames[]` array
4. Modify Python driver if needed

## License

This project is part of the ObsyBox observatory automation system. See LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review Arduino serial monitor output
- Test with the provided test scripts
- Verify network connectivity and configuration