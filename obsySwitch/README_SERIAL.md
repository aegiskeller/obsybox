# ObsyBox Relay Controller - Serial Version

Arduino-based relay switch controller for observatory automation with ASCOM driver interface via USB Serial.

## Overview

This is the **USB Serial version** of the ObsyBox Relay Controller. It provides direct serial communication between your computer and Arduino for reliable, simple relay control - perfect for ASCOM/NINA integration.

## What's Included

### Core Files
- **`RelayController_Serial/`** - Arduino sketch for serial communication
- **`obsyswitch_serial_driver.py`** - Python ASCOM-compatible driver
- **`ascom_switch_server.py`** - ASCOM web server for NINA integration
- **`nina_serial_integration.py`** - Direct NINA integration scripts
- **`ascomDriver/`** - Windows ASCOM driver (C#)

### Documentation
- **`ASCOM_USAGE_GUIDE.md`** - How to use the ASCOM interface
- **`NINA_INTEGRATION_GUIDE.md`** - Detailed NINA setup
- **`NINA_SETUP_GUIDE.md`** - Quick start for NINA
- **`RELAY_JUMPER_GUIDE.md`** - Hardware wiring guide

### Test & Diagnostic Tools
- **`test_arduino_serial.py`** - Test basic serial communication
- **`test_all_relays.py`** - Test all relay operations
- **`relay_diagnostic.py`** - Diagnostic tool
- **`relay_sequence_demo.py`** - Demo automation sequences

## Quick Start

### 1. Hardware Setup
Connect Arduino to computer via USB, wire relays per `RELAY_JUMPER_GUIDE.md`

### 2. Upload Arduino Sketch
```bash
# Open Arduino IDE
# Load: RelayController_Serial/RelayController_Serial.ino
# Upload to Arduino
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Test Connection
```bash
python test_arduino_serial.py
```

### 5. Use with NINA
```bash
# Start ASCOM server
python ascom_switch_server.py

# Or use direct integration
python nina_serial_integration.py startup
```

## Why Serial Version?

**Simple** - Direct USB connection, no network setup  
**Reliable** - No WiFi/network issues  
**Fast** - Low latency serial communication  
**Portable** - Works anywhere with USB  
**ASCOM Compatible** - Full ASCOM Switch interface

## Support

See the included documentation files for detailed setup and troubleshooting.
