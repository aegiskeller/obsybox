# NINA → ASCOM → Arduino Relay Control Integration Guide

Complete pathway documentation for controlling Arduino relay switches from NINA scheduling software through ASCOM drivers.

## Overview

This integration enables NINA (Nighttime Imaging 'N' Astronomy) to control your Arduino-based relay switches through ASCOM drivers. Perfect for automating mount power, cameras, dew heaters, and other observatory equipment.

**Architecture Flow:**
```
NINA Sequence → ASCOM Switch Driver → USB Serial → Arduino Uno → 4-Channel Relay Module → Equipment
```

## Hardware Requirements

### Arduino Setup
- **Arduino Uno R3** (or compatible)
- **4-Channel Relay Module** (5V, active LOW)
- **USB Cable** (Type A to Type B)
- **Jumper Wires** for relay connections

### Relay Connections
```
Arduino Pin → Relay Module
Pin 2       → IN1 (Relay 1 - Mount)
Pin 3       → IN2 (Relay 2 - Camera)
Pin 4       → IN3 (Relay 3 - Dew Heater)
Pin 5       → IN4 (Relay 4 - Focuser)
5V          → VCC
GND         → GND
```

### Power Connections (High Voltage - BE CAREFUL!)
```
Relay 1 NO/COM → Mount Power Supply (120V/240V)
Relay 2 NO/COM → Camera Power Supply
Relay 3 NO/COM → Dew Heater Controller
Relay 4 NO/COM → Focuser Power Supply
```

⚠️  **SAFETY WARNING:** Relay outputs handle mains voltage. Only qualified personnel should wire high voltage connections. Use proper enclosures and safety practices.

## Software Installation

### 1. Arduino Sketch Upload
Upload `RelayController_Serial.ino` to your Arduino:

```bash
# Using arduino-cli
./bin/arduino-cli compile --fqbn arduino:avr:uno obsySwitch/RelayController_Serial
./bin/arduino-cli upload --fqbn arduino:avr:uno --port /dev/cu.usbserial-XXXX obsySwitch/RelayController_Serial

# Using Arduino IDE
# Open RelayController_Serial.ino
# Select Board: Arduino Uno
# Select correct Port
# Click Upload
```

### 2. Python Dependencies
Install required Python packages:

```bash
pip install pyserial
```

### 3. Driver Files
Copy these files to your ASCOM driver directory:
- `obsyswitch_serial_driver.py`
- `nina_serial_integration.py` (created below)

## NINA Integration

### 1. ASCOM Driver Setup

The Python ASCOM driver provides a bridge between NINA and the Arduino:

```python
from obsyswitch_serial_driver import ASCOMSwitchSerial

# Create ASCOM-compatible switch driver
switch_driver = ASCOMSwitchSerial()

# Connect to Arduino (auto-detects port)
switch_driver.Connected = True

# Control switches (0-based indexing)
switch_driver.SetSwitch(0, True)   # Turn on Mount
switch_driver.SetSwitch(1, True)   # Turn on Camera
switch_driver.SetSwitch(2, False)  # Turn off Dew Heater
switch_driver.SetSwitch(3, True)   # Turn on Focuser

# Get switch states
mount_on = switch_driver.GetSwitch(0)
camera_on = switch_driver.GetSwitch(1)
```

### 2. Switch Mappings

The Arduino sketch defines these switch mappings:

| Switch ID | NINA Index | Name | Description | Arduino Pin |
|-----------|------------|------|-------------|-------------|
| 0 | 0 | Mount | Telescope mount power | Pin 2 |
| 1 | 1 | Camera | Main imaging camera | Pin 3 |
| 2 | 2 | Dew Heater | Dew prevention system | Pin 4 |
| 3 | 3 | Focuser | Electronic focuser | Pin 5 |

### 3. NINA Sequence Integration

#### Method 1: Direct ASCOM Switch Control

In NINA, add "Switch" instructions to your sequences:

1. **Sequence Start** → Add "Switch" instruction
   - Device: "ObsyBox Relay Switch - Serial"
   - Switch: "Mount" (Index 0)
   - Action: "Turn On"

2. **Imaging Block** → Add switch controls
   - Before imaging: Turn on Camera, Focuser
   - After imaging: Turn off unnecessary equipment

3. **Sequence End** → Emergency shutdown
   - Turn off all switches for safety

#### Method 2: Python Integration Script

For more complex control logic, use the integration script:

```python
# nina_serial_integration.py
from obsyswitch_serial_driver import ObsySwitchSerialController
import time
import logging

def startup_sequence():
    """Power on equipment in proper order"""
    controller = ObsySwitchSerialController()
    
    try:
        controller.connect()
        
        # Startup sequence
        print("🔌 Starting observatory equipment...")
        
        controller.set_switch(0, True)   # Mount first
        time.sleep(2)
        
        controller.set_switch(1, True)   # Camera
        time.sleep(1)
        
        controller.set_switch(3, True)   # Focuser
        time.sleep(1)
        
        # Dew heater based on conditions
        if check_dew_conditions():
            controller.set_switch(2, True)
            
        print("✅ Startup sequence complete")
        
    finally:
        controller.disconnect()

def shutdown_sequence():
    """Safely power down all equipment"""
    controller = ObsySwitchSerialController()
    
    try:
        controller.connect()
        
        print("🔄 Shutting down observatory...")
        
        # Turn off everything
        controller.emergency_stop()
        
        print("✅ All equipment powered off")
        
    finally:
        controller.disconnect()

def check_dew_conditions():
    """Check if dew heater should be activated"""
    # Add your dew point logic here
    # Could integrate with weather monitoring
    return True  # Placeholder

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "startup":
            startup_sequence()
        elif sys.argv[1] == "shutdown":
            shutdown_sequence()
        else:
            print("Usage: python nina_serial_integration.py [startup|shutdown]")
    else:
        # Interactive mode
        startup_sequence()
```

#### Method 3: NINA External Script Integration

Configure NINA to call Python scripts:

1. **Add External Script Instruction**
   - Program: `python`
   - Arguments: `/path/to/nina_serial_integration.py startup`
   - Working Directory: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch`

2. **Sequence Structure:**
```
Sequence Start
├── External Script: Startup Equipment
├── Cool Camera
├── Slew to Target
├── Auto Focus
├── Start Imaging
└── Sequence End
    ├── Stop Imaging
    ├── Warm Camera
    └── External Script: Shutdown Equipment
```

## Testing & Troubleshooting

### 1. Arduino Communication Test

Test the Arduino directly:

```python
python obsyswitch_serial_driver.py
```

Expected output:
```
Testing ObsyBox Relay Controller - USB Serial Version
============================================================
Connecting to Arduino...
✅ Connected successfully!
📱 Device: ObsyBox Relay Controller v1.0
💾 Firmware: 1.0.0
⏱️  Uptime: 45.2 seconds
🧠 Free RAM: 1547 bytes

🔌 Available switches: 4
  Switch 0 (Mount): OFF
  Switch 1 (Camera): OFF
  Switch 2 (Dew Heater): OFF
  Switch 3 (Focuser): OFF

🧪 Testing switch control...
Testing Mount relay (Switch 0)...
  Original state: OFF
  Toggling...
  New state: ON
  Toggling back...
  Final state: OFF
  ✅ Switch control test passed!

🎉 All tests completed successfully!
```

### 2. Serial Port Detection

If auto-detection fails, manually specify the port:

```python
# macOS/Linux
controller = ObsySwitchSerialController("/dev/cu.usbserial-14120")

# Windows  
controller = ObsySwitchSerialController("COM3")
```

Find your Arduino port:
```bash
# macOS/Linux
ls /dev/cu.usb* /dev/ttyUSB* /dev/ttyACM*

# Windows
# Check Device Manager → Ports (COM & LPT)
```

### 3. Common Issues

#### Arduino Not Responding
- Check USB cable connection
- Verify correct sketch uploaded
- Ensure no other software using serial port
- Try different USB port
- Reset Arduino and reconnect

#### Permission Errors (macOS/Linux)
```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER

# Check port permissions (macOS)
ls -la /dev/cu.usbserial*
```

#### Import Errors
```bash
# Install missing dependencies
pip install pyserial

# Check Python path
python -c "import serial; print(serial.__file__)"
```

#### Relay Not Switching
- Check wiring connections
- Verify relay module power (5V)
- Test with multimeter
- Check relay active LOW vs HIGH
- Verify pin assignments in sketch

## Safety Features

### 1. Emergency Stop
All software includes emergency stop functionality:

```python
# Turn off all relays immediately
controller.emergency_stop()
```

### 2. Connection Monitoring
The driver includes automatic connection monitoring:
- Ping/pong heartbeat every 30 seconds
- Auto-reconnection on communication failure
- Timeout protection for commands

### 3. State Persistence
Arduino saves relay states to EEPROM:
- Power-on state restoration
- Protection against accidental resets
- Configuration backup

### 4. Hardware Protections
- Individual LED indicators per relay
- Fuse protection on high-voltage connections
- Optoisolated relay modules recommended
- Emergency manual switches parallel to Arduino control

## Advanced Configuration

### 1. Custom Switch Names
Modify the Arduino sketch to change switch names:

```cpp
// In RelayController_Serial.ino
const char* RELAY_NAMES[NUM_RELAYS] = {
  "Mount", "Camera", "Dew Heater", "Focuser"
};
```

### 2. Startup Delays
Add delays between relay activation:

```cpp
// Custom startup sequence
void powerOnSequence() {
  setRelay(1, true);  // Mount first
  delay(2000);
  
  setRelay(2, true);  // Camera
  delay(1000);
  
  setRelay(4, true);  // Focuser
  delay(500);
  
  setRelay(3, true);  // Dew heater last
}
```

### 3. Environmental Integration
Connect to weather monitoring:

```python
def should_activate_dew_heater():
    """Check weather conditions for dew heater"""
    import requests
    
    # Get current conditions
    weather = requests.get("http://192.168.1.183/humidity").json()
    humidity = weather.get("humidity", 0)
    
    # Activate if humidity > 80%
    return humidity > 80.0
```

## Production Deployment

### 1. Enclosure Setup
- Use weatherproof electrical enclosure
- Install DIN rail for relay modules
- Add ventilation fans if needed
- Include manual override switches
- Label all connections clearly

### 2. Network Integration
- Document IP addresses used
- Configure static DHCP reservations
- Set up monitoring alerts
- Create backup configurations

### 3. Documentation
- Create wiring diagrams
- Document switch assignments
- Include troubleshooting steps
- Train other users

### 4. Backup Plans
- Keep spare Arduino programmed
- Document recovery procedures
- Include manual control options
- Test emergency procedures regularly

## Integration with ObsyBox Ecosystem

This relay controller integrates with other ObsyBox components:

### Weather Safety Integration
```python
def check_weather_safety():
    """Check weather before turning on equipment"""
    import paho.mqtt.client as mqtt
    
    client = mqtt.Client()
    client.connect("192.168.1.49", 1883)
    
    # Check weather safety status
    safety_msg = client.subscribe("obsybox/weathersafety")
    
    if safety_msg and safety_msg.get("safe", False):
        return True
    return False

def safe_power_on():
    """Only power on if weather is safe"""
    if check_weather_safety():
        startup_sequence()
    else:
        print("⚠️  Weather unsafe - equipment remains off")
```

### MQTT Integration
```python
def publish_relay_status():
    """Publish relay status to MQTT"""
    import paho.mqtt.client as mqtt
    import json
    
    controller = ObsySwitchSerialController()
    controller.connect()
    
    status = controller.get_all_switches()
    
    client = mqtt.Client()
    client.connect("192.168.1.49", 1883)
    client.publish("obsybox/relays", json.dumps(status))
    
    controller.disconnect()
```

## Next Steps

1. **Upload Arduino Sketch**: Flash `RelayController_Serial.ino` to your Arduino
2. **Test Communication**: Run the Python test script
3. **Configure NINA**: Add switch instructions to sequences
4. **Test Integration**: Run a complete startup/shutdown cycle
5. **Monitor Operations**: Watch for any communication issues
6. **Document Settings**: Record your specific configuration

This completes the full NINA → ASCOM → Arduino → Relay pathway! The system provides reliable, automated control of your observatory equipment through NINA's scheduling system.