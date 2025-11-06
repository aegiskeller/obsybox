# NINA Watchdog - Observatory Safety Monitor

🐕 **Automated safety monitoring for NINA with dark theme GUI and emergency shutdown**

## Quick Setup for NINA Integration

### 1. Install Dependencies
```powershell
cd C:\Users\aegis\Documents\obsybox\nina_watchdog
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Settings
Edit `nina_safety_config.json`:
- Add your Pushover API tokens for mobile alerts
- Set ASCOM driver names (telescope/dome)
- Configure weather thresholds and safety limits

### 3. Add to NINA External Scripts
1. Open NINA → Options → External Scripts
2. Add new script with path: `C:\Users\aegis\Documents\obsybox\nina_watchdog\nina_quick_launcher.bat`
3. Set to run "Before Sequence Start"
4. Enable "Continue if script fails" for non-blocking operation
```powershell
# Setup Pushover for phone notifications - see PUSHOVER_SETUP.md
# Edit nina_safety_config.json with your Pushover tokens
```

### 3. Verify Installation
```powershell
.\venv\Scripts\python.exe setup.py    # Install dependencies and check system
```

### 3. Test and Deploy
```powershell
.\venv\Scripts\python.exe nina_safety_monitor.py      # Test run
install_safety_service.bat            # Install as Windows service (run as Admin)
```

### 4. Optional: Use Activation Scripts
```powershell
# For easy environment management
.\activate.ps1                        # PowerShell version
# or
activate.bat                          # Command prompt version
```

## 📁 Integration with obsybox
## Features

### 🛡️ Safety Monitoring
- **Real-time MQTT weather data** from obsybox sensors (192.168.1.49:1883)
- **ASCOM telescope/dome control** with emergency parking/closure
- **NINA process monitoring** with automatic crash detection
- **Sun altitude tracking** for daylight safety
- **Wind/rain/cloud monitoring** via ArduSafeMon integration

### 🌙 Dark Theme GUI
- **Professional appearance** matching observatory software aesthetics
- **Color-coded status indicators**: Green=Safe, Yellow=Warning, Red=Critical
- **Watchdog mascot** with custom icon (no more generic Python logos!)
- **System tray integration** - starts minimized, runs in background
- **Real-time status grid** showing all monitored systems

### � Mobile Alerts
- **Pushover notifications** with emergency priority (bypasses Do Not Disturb)
- **Critical alerts** for dome failures, emergency shutdowns, weather events
- **Status updates** for routine monitoring activities

### 🚨 Emergency Response
- **Tiered safety timeouts** with smart condition-based responses
- **51-minute safe timeout**: Stop tracking only (safe conditions)
- **15-minute dawn timeout**: Park telescope & close dome (past astronomical dawn)
- **15-minute emergency timeout**: Full shutdown (unsafe weather conditions)
- **Automatic recovery** when NINA resumes activity

## Core Files

| File | Purpose |
|------|---------|
| `nina_quick_launcher.bat` | **NINA launcher** - quick detached startup |
| `nina_watchdog_script.bat` | **Detailed launcher** - with full diagnostics |
| `watchdog_safety_gui.py` | **Dark theme GUI** with status monitoring |
| `emergency_shutdown.py` | **Emergency handler** with ASCOM control |
| `pushover_notifications.py` | **Mobile alerts** via Pushover API |
| `nina_safety_monitor.py` | **Background monitor** with MQTT integration |
| `nina_safety_config.json` | **Configuration** with API keys and thresholds |
| `requirements.txt` | **Dependencies** for virtual environment |
| `nina_watchdog.ico` | **Custom icon** for professional appearance |

## Tiered Safety Logic

### **🟢 Safe Conditions (51+ minutes inactive)**
- **Action**: Stop telescope tracking only
- **Reason**: Conservative safety measure during long inactivity
- **Recovery**: Automatic when NINA resumes

### **🟡 Past Astronomical Dawn (15+ minutes inactive)**  
- **Action**: Park telescope AND close dome
- **Reason**: Protect equipment from daylight exposure
- **Recovery**: Manual intervention required

### **� Wait State Active**
- **Display**: Orange "WAIT" status in GUI
- **Action**: Normal monitoring continues, timeouts extended
- **Reason**: NINA is in legitimate "Wait for Time" instruction
- **Recovery**: Automatic when wait completes

### **�🔴 Unsafe Weather (15+ minutes inactive)**
- **Action**: Emergency shutdown (park + close + alerts)
- **Reason**: Immediate equipment protection from weather damage
- **Recovery**: Manual intervention after conditions improve

### **💡 Smart Recovery**
All automated actions reset when NINA activity resumes, allowing seamless operation continuation.

### **⏳ Wait Detection**
The system intelligently detects NINA "Wait for Time" instructions and prevents timeouts during legitimate waiting periods:
- **Automatic detection** of waiting states in NINA logs
- **NINA log format support**: Handles `2025-11-02T18:57:48.0157|INFO|SequenceItem.cs|Run|208|Starting Category: Utility, Item: WaitForTime`
- **Smart completion tracking**: Detects `Finishing Category: Utility, Item: WaitForTime` to know when waits end
- **Configurable grace period** (default: 120 minutes) to prevent indefinite waits
- **Smart pattern matching** for various wait instruction formats
- **Seamless integration** with existing safety logic

## Emergency Procedures

### Manual Emergency Shutdown
1. **GUI Method**: Click red "🚨 Emergency Shutdown" button
2. **Script Method**: Run `emergency_shutdown.py` directly
3. **NINA Method**: Stop sequence and trigger external script

### System Recovery
1. **Check logs** in GUI activity window
2. **Verify equipment** status via ASCOM drivers
3. **Reset weather** monitoring via MQTT reconnection
4. **Restart monitoring** using GUI controls

## Troubleshooting

### Common Issues
- **ASCOM not found**: Install ASCOM Platform and drivers
- **MQTT connection failed**: Check ArduSafeMon at 192.168.1.49:1883
- **Pushover not working**: Verify API tokens in config file
- **GUI won't start**: Check virtual environment and dependencies

### Support Files
- **NINA_INTEGRATION_GUIDE.md**: Detailed NINA setup instructions
- **NINA_EXTERNAL_SCRIPT_SETUP.md**: External script configuration
- **README.md**: This file

## Observatory Protection Philosophy

> **Collision Prevention > Weather Protection**

The system prioritizes preventing mechanical damage (telescope hitting dome) over minor weather exposure. Emergency sequences always park telescope before closing dome, even if weather conditions are deteriorating.

## GUI Status Indicators

### **Main Status Display**
- **🟢 SYSTEM NOMINAL**: All systems operating normally
- **🟠 WAIT**: NINA is in "Wait for Time" state (normal operation)
- **🟡 WARNING**: Minor issues detected (yellow indicators)
- **🔴 CRITICAL**: Emergency conditions (red indicators)

### **Individual Component Status**
- **🌐 MQTT Connection**: Weather monitoring link (192.168.1.49:1883)
- **💻 NINA Process**: NINA application running status
- **📝 NINA Activity**: Log activity and wait state detection
- **🌦️ Weather Safety**: ArduSafeMon safety conditions
- **☀️ Sun Altitude**: Day/night status for imaging safety

### **Color Legend**
- **🟢 Green**: Normal operation, all good
- **🟠 Orange**: Wait state active (special status)
- **🟡 Yellow**: Warning condition, monitoring
- **🔴 Red**: Error or unsafe condition

## Configuration

### Wait Detection Settings
The system can detect NINA "Wait for Time" instructions to prevent false timeouts:

```json
"wait_detection": {
  "enable_wait_detection": true,
  "wait_grace_period_minutes": 120,
  "wait_check_lines": 50
}
```

- **`enable_wait_detection`**: Enable/disable automatic wait state detection
- **`wait_grace_period_minutes`**: Maximum time to extend activity window for waits (default: 120 min)
- **`wait_check_lines`**: Number of recent log lines to analyze for wait patterns (default: 50)

#### Observatory Location
```json
"observatory_location": {
  "latitude": -35.0,
  "longitude": 150.0,
  "elevation_meters": 100,
  "name": "Your Observatory"
}
```
- **`latitude`**: Observatory latitude in degrees (negative for Southern Hemisphere)
- **`longitude`**: Observatory longitude in degrees (positive for Eastern Hemisphere)  
- **`elevation_meters`**: Elevation above sea level in meters
- **`name`**: Optional observatory name for logging

#### Safety Checks

This prevents the safety monitor from shutting down equipment during legitimate NINA waiting periods while still providing protection against indefinite hangs.

---

**🐕 Your watchdog is on duty, protecting your observatory 24/7!**