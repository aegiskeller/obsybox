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
2. Add new script with path: `C:\Users\aegis\Documents\obsybox\nina_watchdog\nina_watchdog_script.bat`
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
- **Automatic telescope parking** before dome closure (collision prevention)
- **Sequential shutdown** with safety interlocks and failure recovery
- **Manual emergency button** in GUI for immediate shutdown
- **Enhanced dome failure alerts** with detailed error reporting

## Core Files

| File | Purpose |
|------|---------|
| `nina_watchdog_script.bat` | **NINA launcher** - main entry point |
| `watchdog_safety_gui.py` | **Dark theme GUI** with status monitoring |
| `emergency_shutdown.py` | **Emergency handler** with ASCOM control |
| `pushover_notifications.py` | **Mobile alerts** via Pushover API |
| `nina_safety_monitor.py` | **Background monitor** with MQTT integration |
| `nina_safety_config.json` | **Configuration** with API keys and thresholds |
| `requirements.txt` | **Dependencies** for virtual environment |
| `nina_watchdog.ico` | **Custom icon** for professional appearance |

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

---

**🐕 Your watchdog is on duty, protecting your observatory 24/7!**