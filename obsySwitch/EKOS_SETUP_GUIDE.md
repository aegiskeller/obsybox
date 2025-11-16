# Ekos/KStars Integration Guide for ObsyBox Relay Switch

Complete guide to connecting Ekos (KStars) to your ObsyBox relay controller using INDI-Alpaca bridge.

---

## Overview

**Ekos uses INDI, not ASCOM**. Your ObsyBox switch has ASCOM Alpaca support, so you need:
1. **ASCOM Alpaca Server** (you already have this)
2. **INDI Alpaca Driver** (bridge between INDI and ASCOM)

This allows Ekos to control your relays through the INDI protocol by translating to ASCOM Alpaca API calls.

---

## Prerequisites

### 1. Hardware
- Arduino with `RelayController_Serial` sketch uploaded
- USB connection to Mac
- 4-channel relay board wired correctly

### 2. Software Requirements

#### Install KStars (includes INDI and Ekos)

**macOS Installation:**

KStars for macOS comes with INDI and Ekos built-in. Download from:
- **Official**: https://edu.kde.org/kstars/#download
- **Direct DMG**: https://www.indilib.org/download.html

Or use Homebrew cask:
```bash
# Install KStars (includes Ekos and INDI)
brew install --cask kstars
```

**Note:** INDI is not available as a standalone package on macOS. You must install KStars, which bundles INDI drivers.

#### Install Python Dependencies
```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch
pip install -r requirements.txt
# or
pip install flask pyserial
```

---

## Step-by-Step Setup

### Step 1: Start the ASCOM Alpaca Server

The Alpaca server bridges between your Arduino (USB Serial) and network protocols.

```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch
python ascom_switch_server.py
```

**Expected output:**
```
Starting ObsyBox ASCOM Switch Server
==================================================
Server URL: http://localhost:8080
ASCOM API: http://localhost:8080/api/v1/switch/0/
Status: http://localhost:8080/status
Stop server: Ctrl+C
==================================================
```

**Test the server:**
```bash
# In another terminal
curl http://localhost:8080/status
```

You should see JSON with device status and switch information.

**Keep this terminal running!** The server must be active for Ekos to connect.

---

### Step 2: Configure INDI for Alpaca (macOS Specific)

**Important for macOS:** INDI's Alpaca driver may not be included in the KStars macOS bundle. Instead, we'll use **direct REST API integration** or a **custom Python INDI driver**.

#### Option A: Use Ekos External Scripts (Simplest)

Skip INDI driver complexity and use Ekos's built-in external script support:

1. Ekos can run shell scripts for device control
2. Scripts call your Alpaca REST API directly
3. No INDI driver needed!

See "Alternative: REST API Integration" section below.

#### Option B: Check for INDI Alpaca in KStars Bundle

After installing KStars, check if Alpaca driver is included:

```bash
# Find KStars installation
ls /Applications/KStars.app/Contents/MacOS/

# Check for INDI drivers
ls /Applications/KStars.app/Contents/Resources/indi/ 2>/dev/null || \
ls ~/Library/Application\ Support/kstars/indi/ 2>/dev/null

# Look for Alpaca or HTTP drivers
find /Applications/KStars.app -name "*alpaca*" -o -name "*http*" 2>/dev/null
```

#### Option C: Build INDI Alpaca from Source (Advanced)

Only if you need the official INDI driver:

```bash
# Install dependencies
brew install cmake qt@5 cfitsio gsl

# Clone INDI 3rd party drivers
git clone https://github.com/indilib/indi-3rdparty.git
cd indi-3rdparty/indi-alpaca

# Build (may require fixing macOS-specific issues)
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make
sudo make install
```

**Note:** Building INDI drivers on macOS can be challenging. **Option A (External Scripts) is recommended** for macOS users.

---

### Step 3: Start INDI Server (If Using INDI Driver)

**Only needed if you successfully installed INDI Alpaca driver in Step 2.**

KStars/Ekos usually manages INDI server automatically, but you can start it manually:

```bash
# Check if indiserver is available
which indiserver

# If available, start with Alpaca driver
indiserver -v indi_alpaca_switch

# Or on specific port
indiserver -p 7624 indi_alpaca_switch
```

**For macOS KStars users:** Skip this step and let Ekos manage INDI server automatically through the KStars profile manager.

---

### Step 4: Configure Ekos/KStars

#### 4.1 Open Ekos Profile Manager

1. Launch **KStars**
2. Go to **Tools** → **Ekos**
3. Click **Profile** button

#### 4.2 Create New Profile (or Edit Existing)

1. Click **New Profile** or select existing profile
2. Name it: `ObsyBox Observatory`

#### 4.3 Add Switch Equipment

In the profile configuration:

1. **Connection**: Select `Local` (INDI server on same machine)
   - Or `Remote` if running on different machine, enter IP address

2. Find **Auxiliary** section or **Additional Devices**

3. Add equipment:
   - **Type**: Switch
   - **Driver**: `INDI Alpaca Switch` or `Alpaca Switch`
   - **Mode**: Local or Remote

4. Click **Save**

#### 4.4 Configure Alpaca Connection

After starting the profile:

1. In Ekos, find the **Switch** panel
2. Click the **Options** or **Setup** button
3. Configure Alpaca connection:
   - **Host**: `localhost` (or `127.0.0.1`)
   - **Port**: `8080`
   - **Device Number**: `0`
   - **Device Type**: `Switch`

4. Click **Connect**

---

### Step 5: Test Switch Control

#### 5.1 Verify Connection

In Ekos:
1. Switch panel should show **Connected** status
2. You should see 4 switches listed:
   - Switch 0: Mount
   - Switch 1: Camera
   - Switch 2: Focuser
   - Switch 3: Aux

#### 5.2 Test Manual Control

1. Click switches ON/OFF in Ekos interface
2. Watch Arduino relay board LEDs change
3. Verify relays click when toggling

#### 5.3 Monitor Server Logs

Check the Alpaca server terminal for activity:
```
GET /api/v1/switch/0/getswitch/0
PUT /api/v1/switch/0/setswitch/0
```

---

## Alternative: Direct INDI Driver (Advanced)

If the INDI-Alpaca bridge doesn't work, you can create a native INDI driver.

### Quick INDI Driver Script

Save as `indi_obsybox_switch.py`:

```python
#!/usr/bin/env python3
"""
INDI Driver for ObsyBox Relay Switch
Provides native INDI interface without Alpaca bridge
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from obsyswitch_serial_driver import ObsySwitchSerialController

# INDI PyIndi wrapper
try:
    import PyIndi
except ImportError:
    print("Error: PyIndi not installed")
    print("Install with: pip install pyindi-client")
    sys.exit(1)

class ObsyBoxSwitch(PyIndi.BaseDevice):
    def __init__(self):
        super().__init__()
        self.controller = ObsySwitchSerialController()
        
    def initProperties(self):
        # Define INDI switch properties
        self.switches = []
        switch_names = ["Mount", "Camera", "Focuser", "Aux"]
        
        for i, name in enumerate(switch_names):
            switch_prop = self.switch(f"SWITCH_{i}", name, "Controls")
            switch_prop.load()
            self.switches.append(switch_prop)
    
    def ISNewSwitch(self, dev, name, states, names):
        # Handle switch state changes from Ekos
        for i, switch in enumerate(self.switches):
            if name == switch.name:
                state = states[0]
                self.controller.set_switch(i, state == PyIndi.ISS_ON)
                return True
        return False

if __name__ == "__main__":
    # Run INDI driver
    driver = ObsyBoxSwitch()
    driver.run()
```

**Usage:**
```bash
# Make executable
chmod +x indi_obsybox_switch.py

# Run as INDI driver
./indi_obsybox_switch.py
```

Then in Ekos, select this as a custom driver.

---

## Configuration Details

### Switch Mappings

| Switch ID | Name    | Purpose                      | Arduino Pin |
|-----------|---------|------------------------------|-------------|
| 0         | Mount   | Telescope mount power        | Relay 1     |
| 1         | Camera  | Imaging camera power         | Relay 2     |
| 2         | Focuser | Electronic focuser power     | Relay 3     |
| 3         | Aux     | Auxiliary equipment          | Relay 4     |

### ASCOM Alpaca API Endpoints

Your server provides these endpoints (used by INDI bridge):

```
GET  /api/v1/switch/0/connected          - Connection status
PUT  /api/v1/switch/0/connected          - Connect/disconnect
GET  /api/v1/switch/0/maxswitch          - Number of switches (3 = 4 switches)
GET  /api/v1/switch/0/getswitch/{id}     - Get switch state
PUT  /api/v1/switch/0/setswitch/{id}     - Set switch state
GET  /api/v1/switch/0/getswitchname/{id} - Get switch name
```

---

## Using Switches in Ekos Scheduler

### Power-On Sequence

1. Open Ekos **Scheduler**
2. Create new job
3. Add **Pre-Job Script** or **Startup Procedure**:
   - Turn on Mount (Switch 0)
   - Wait 5 seconds
   - Turn on Camera (Switch 1)
   - Turn on Focuser (Switch 2)

### Shutdown Sequence

1. In scheduler **Shutdown Procedure**:
   - Park telescope
   - Turn off Camera (Switch 1)
   - Turn off Focuser (Switch 2)
   - Turn off Mount (Switch 0)

### Emergency Stop

Configure **Abort** action:
- Turn off all switches
- Use Alpaca API emergency stop:
  ```bash
  curl -X PUT http://localhost:8080/api/v1/switch/0/action \
    -H "Content-Type: application/json" \
    -d '{"Action":"Emergency_Stop","Parameters":""}'
  ```

---

## Troubleshooting

### Issue: INDI can't find Alpaca driver

**Solution:**
```bash
# Check INDI drivers installed
ls /usr/local/share/indi/

# Manually specify driver path
indiserver -v /path/to/indi_alpaca_switch

# Or use generic INDI HTTP driver
indiserver indi_http_driver
```

### Issue: Connection fails in Ekos

**Checks:**
1. ✅ Alpaca server running? (`curl http://localhost:8080/status`)
2. ✅ Arduino connected? Check `/dev/cu.usbserial*`
3. ✅ INDI server running? (`ps aux | grep indiserver`)
4. ✅ Correct port in Ekos? (8080 for Alpaca)
5. ✅ Firewall blocking? (check macOS Security settings)

**Test connection manually:**
```bash
# Test INDI server
telnet localhost 7624

# Test Alpaca server
curl http://localhost:8080/api/v1/switch/0/name
```

### Issue: Switches don't respond

**Debug steps:**
1. Check Alpaca server logs for API requests
2. Test switch directly:
   ```bash
   curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/0 \
     -H "Content-Type: application/json" \
     -d '{"State":true}'
   ```
3. Check Arduino serial connection:
   ```bash
   python -c "from obsyswitch_serial_driver import *; \
              c=ObsySwitchSerialController(); c.connect(); \
              print(c.get_device_info())"
   ```

### Issue: INDI bridge not translating correctly

**Workaround - Direct Python Script:**

Create `ekos_switch_control.py`:
```python
#!/usr/bin/env python3
from obsyswitch_serial_driver import ObsySwitchSerialController
import sys

controller = ObsySwitchSerialController()
controller.connect()

if sys.argv[1] == "on":
    controller.set_switch(int(sys.argv[2]), True)
elif sys.argv[1] == "off":
    controller.set_switch(int(sys.argv[2]), False)

controller.disconnect()
```

Use in Ekos scripts:
```bash
python ekos_switch_control.py on 0   # Turn on mount
python ekos_switch_control.py off 0  # Turn off mount
```

---

## Network Configuration (Optional)

### Run Server on Network

To access from other computers (remote Ekos):

```bash
# Start server on all interfaces
python ascom_switch_server.py
# Server runs on 0.0.0.0:8080
```

Update Ekos configuration:
- **Host**: `192.168.1.xxx` (your Mac's IP)
- **Port**: `8080`

**Firewall:**
```bash
# Allow incoming connections on port 8080
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblock python3
```

---

## Quick Reference

### Start Everything

Terminal 1 - Alpaca Server:
```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch
python ascom_switch_server.py
```

Terminal 2 - INDI Server (if using INDI bridge):
```bash
indiserver -v indi_alpaca_switch
```

### Test Connection Chain

```bash
# 1. Test Arduino connection
python -c "from obsyswitch_serial_driver import *; \
           c=ObsySwitchSerialController(); c.connect(); \
           print('Connected!' if c.is_connected() else 'Failed')"

# 2. Test Alpaca server
curl http://localhost:8080/status

# 3. Test switch control
curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/0 \
  -H "Content-Type: application/json" -d '{"State":true}'

# 4. Launch Ekos and connect
```

---

## Summary

**Connection Flow:**
```
Ekos/KStars 
    ↓ (INDI protocol)
INDI Server (port 7624)
    ↓ (INDI-Alpaca bridge)
ASCOM Alpaca Server (port 8080)
    ↓ (HTTP/REST API)
Python Driver (ascom_switch_server.py)
    ↓ (USB Serial)
Arduino Relay Controller
    ↓ (Digital I/O)
4-Channel Relay Board
    ↓ (12V switching)
Observatory Equipment
```

**Key Points:**
- ✅ Always start Alpaca server first
- ✅ Configure correct host/port in Ekos (localhost:8080)
- ✅ INDI-Alpaca bridge translates protocols automatically
- ✅ Monitor Alpaca server logs for debugging
- ✅ Use emergency stop for safety

**Support:**
- INDI docs: https://www.indilib.org/
- Alpaca protocol: https://ascom-standards.org/Developer/Alpaca.htm
- KStars/Ekos: https://edu.kde.org/kstars/

---

## Alternative: REST API Integration

If INDI bridge is problematic, use Ekos **External Scripts** feature:

Create helper scripts in `obsySwitch/ekos_scripts/`:

**power_on_all.sh:**
```bash
#!/bin/bash
curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/0 -d '{"State":true}'
curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/1 -d '{"State":true}'
curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/2 -d '{"State":true}'
```

**power_off_all.sh:**
```bash
#!/bin/bash
curl -X PUT http://localhost:8080/api/v1/switch/0/action \
  -H "Content-Type: application/json" \
  -d '{"Action":"Emergency_Stop","Parameters":""}'
```

Make executable and use in Ekos scheduler scripts!
