# NINA Integration Guide for ObsyBox ASCOM Relay Switch

## Quick Start Summary

Your Arduino Uno relay controller now appears as a native ASCOM Switch device in NINA! Here's how to set it up and use it.

## Step-by-Step NINA Setup

### 1. Start the ASCOM Server (Required First!)

```bash
cd obsySwitch
python alpaca_switch_server.py
```

You should see:
```
 Starting ObsyBox ASCOM Alpaca Switch Server
 Server URL: http://localhost:11111
 ASCOM API: http://localhost:11111/api/v1/switch/0/
 NINA Discovery Instructions:
1. Equipment  Switch  ASCOM Switch
2. Setup  Enter: http://localhost:11111
3. Connect and test switches
```

### 2. Configure NINA Equipment

#### Open NINA Equipment Tab
1. Launch NINA
2. Go to **Equipment** tab (wrench icon)
3. Find the **Switch** section

#### Add ASCOM Switch Device
1. Click the **gear icon**  next to Switch
2. Select **"ASCOM Switch"** from the dropdown
3. Click **"Choose ASCOM Switch"** button

#### Configure ASCOM Alpaca Device  
1. In the ASCOM Switch chooser dialog:
   - Click **"Alpaca Discovery"** button
   - **OR** manually enter: `http://localhost:11111`
2. Select **"ObsyBox Relay Switch"** from the discovered devices
3. Click **OK**

#### Connect to the Switch
1. Back in NINA Equipment tab
2. Click **"Connect"** button next to the Switch
3. You should see **"Connected"** status
4. The switch panel will show your 4 relays:
   - **Switch 0: Mount** - Telescope mount power
   - **Switch 1: Camera** - Imaging camera power  
   - **Switch 2: Focuser** - Electronic focuser power
   - **Switch 3: Aux** - Auxiliary equipment power

### 3. Test the Switches

#### Manual Testing in Equipment Tab
1. In the NINA Equipment  Switch section
2. Click the **toggle buttons** next to each switch name
3. You should **hear the relays clicking** on your Arduino
4. The LED indicators should change state
5. Verify each relay works: Mount, Camera, Focuser, Aux

#### Switch Names in NINA
- **Switch 0**: Mount (Pin 2)
- **Switch 1**: Camera (Pin 3) 
- **Switch 2**: Focuser (Pin 4)
- **Switch 3**: Aux (Pin 5)

## Using Switches in NINA Sequences

### 4. Add Switch Instructions to Sequences

#### In Sequence Tab
1. Go to **Sequences** tab
2. Create or open a sequence
3. Drag **"Switch Instruction"** from the instruction panel
4. Configure the switch instruction:
   - **Switch ID**: 0 (Mount), 1 (Camera), 2 (Focuser), or 3 (Aux)
   - **Switch Value**: True (ON) or False (OFF)

#### Example Observatory Startup Sequence
```
1. Switch Instruction - Mount (ID: 0)  ON
    Wait 2 seconds
2. Switch Instruction - Camera (ID: 1)  ON  
    Wait 5 seconds
3. Switch Instruction - Focuser (ID: 2)  ON
    Wait 2 seconds
4. Cool Camera instruction
5. Slew to target instruction
6. Take Exposure instruction
```

#### Example Observatory Shutdown Sequence  
```
1. Warm Camera instruction
2. Park Mount instruction
3. Switch Instruction - Focuser (ID: 2)  OFF
4. Switch Instruction - Camera (ID: 1)  OFF
5. Switch Instruction - Mount (ID: 0)  OFF
```

### 5. Advanced Sequence Usage

#### Conditional Switch Control
- Use **"Loop Condition"** instructions to control switches based on conditions
- Example: Turn on dew heater (Aux) only if humidity > 80%

#### Event-Based Switching
- Use **"Events"** to trigger switch actions
- Example: Turn off all equipment if weather becomes unsafe

#### Target-Based Switching  
- Different switch configurations for different targets
- Example: Turn on guide camera only for long exposures

## Troubleshooting

### Common Issues

#### Switch Not Appearing in NINA
-  **Check**: Is the Alpaca server running? (`python alpaca_switch_server.py`)
-  **Check**: Is Arduino connected via USB?
-  **Check**: Can you access http://localhost:11111/status in browser?

#### "Not Connected" Error
-  **Check**: Arduino USB cable connection
-  **Check**: Arduino programmed with `RelayController_Serial.ino`
-  **Check**: No other software using the serial port (Arduino IDE Serial Monitor)

#### Relays Not Clicking
-  **Check**: Relay module power (red LED should be on)
-  **Check**: Jumper configuration (see `RELAY_JUMPER_GUIDE.md`)
-  **Check**: All connections secure

### Diagnostic Commands

#### Test Server Status
```bash
curl http://localhost:11111/status
```

#### Test Switch Control
```bash
# Turn ON mount relay
curl -X PUT "http://localhost:11111/api/v1/switch/0/setswitch" -d "Id=0&State=true&ClientID=1&ClientTransactionID=1"

# Turn OFF mount relay  
curl -X PUT "http://localhost:11111/api/v1/switch/0/setswitch" -d "Id=0&State=false&ClientID=1&ClientTransactionID=2"
```

#### Run Full Test Suite
```bash
python test_alpaca_server.py
```

## Production Use Tips

### 1. Startup Script
Create a script to auto-start the server:
```bash
#!/bin/bash
cd /path/to/obsybox/obsySwitch
python alpaca_switch_server.py &
```

### 2. Auto-Start with System
Add to your system startup scripts so the ASCOM server starts automatically when your observatory computer boots.

### 3. Monitoring
- Keep the server terminal open to monitor switch activity
- Check `/status` endpoint periodically for device health
- Use the web interface at http://localhost:11111 for status

### 4. Safety Considerations
- Always include **proper wait times** between switch operations
- Test sequences thoroughly before unattended operation
- Consider adding **weather safety checks** before powering equipment

## Switch Naming Convention

| Switch ID | Name | Arduino Pin | Typical Use |
|-----------|------|-------------|-------------|
| 0 | Mount | Pin 2 | Telescope mount power |
| 1 | Camera | Pin 3 | Main imaging camera |
| 2 | Focuser | Pin 4 | Electronic focuser |  
| 3 | Aux | Pin 5 | Auxiliary (dew heater, guide cam, etc.) |

## Integration with ObsyBox Ecosystem

Your relay switch now integrates with the existing ObsyBox components:
- **ArduSafeMon**: Weather safety monitoring
- **NINA Scheduling**: Automated target selection  
- **Dew Heater Control**: Environmental management
- **Monitor Cam**: AllSky imaging

The switch can be controlled based on weather conditions, target schedules, and safety requirements for complete observatory automation.

---

 **You now have professional-grade ASCOM switch control directly in NINA!**

Your Arduino Uno appears as a native ASCOM device alongside your mount, camera, and other observatory equipment. Use it for automated startup/shutdown sequences, equipment power management, and advanced observatory automation workflows.