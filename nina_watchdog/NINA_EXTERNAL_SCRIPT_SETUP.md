# 🌟 NINA External Script Integration Guide

## Overview
This guide shows how to integrate the NINA Safety Monitor as an external script within NINA, providing seamless observatory safety monitoring during your imaging sessions.

## 🚀 Quick Setup

### Step 1: Open NINA External Scripts
1. **Launch NINA**
2. Go to **Tools** → **External Scripts** (or **Options** → **External Scripts**)
3. Click **"Add"** or **"+"** to create a new script

### Step 2: Configure the Script
Fill in these exact values:

| Field | Value |
|-------|-------|
| **Name** | `NINA Watchdog Safety Monitor` |
| **Executable** | `C:\Users\aegis\Documents\obsybox\nina_watchdog\nina_watchdog_script.bat` |
| **Arguments** | *(leave blank)* |
| **Working Directory** | *(leave blank)* |
| **Description** | `Observatory safety monitoring with emergency shutdown` |

### Step 3: Test the Integration
1. Click **"Test"** or **"Run"** in NINA's external scripts dialog
2. You should see a command window briefly showing startup progress
3. The Safety Monitor GUI will launch and minimize to system tray
4. Look for the safety monitor icon in your system tray
5. Monitoring begins automatically within 1 second

## 🎯 NINA Usage Workflow

### Starting Your Session
1. **Launch NINA** as usual
2. **Run the external script**: Tools → External Scripts → "NINA Safety Monitor" → Run
3. **Verify system tray icon** appears
4. **Continue with normal NINA operations**

### During Your Session
- **Automatic monitoring** runs in background
- **Real-time weather checking** via MQTT
- **NINA process monitoring** ensures health
- **Phone alerts** for critical issues (via Pushover)

### If Emergency Occurs
1. **Instant phone notification** with details
2. **Automatic telescope park** (if connected via ASCOM)
3. **Automatic dome closure** (if connected via ASCOM)
4. **NINA process termination** (if unresponsive)
5. **Accessory shutdown** via MQTT

## 📱 System Tray Features

### Right-click Menu Options:
- **Show/Hide Window** - Toggle main GUI visibility
- **Emergency Shutdown** - Manual emergency trigger
- **Refresh Status** - Update equipment connections
- **Exit** - Close safety monitor

### Status Indicators:
- **Green**: All systems normal, monitoring active
- **Yellow**: Warning conditions detected
- **Red**: Critical issues, emergency shutdown triggered

## 🔧 Advanced Integration

### Multiple NINA Profiles
Create separate external scripts for different observing setups:

1. **Visual Observing**: Basic monitoring only
   - Name: `Safety Monitor - Visual`
   - Same script, different name for organization

2. **Imaging Session**: Full monitoring with emergency shutdown
   - Name: `Safety Monitor - Imaging` 
   - Standard configuration

3. **Remote Operation**: Enhanced alerting
   - Name: `Safety Monitor - Remote`
   - Same script, relies on Pushover for alerts

### Sequence Integration
Add the safety monitor to NINA sequences:

1. **Sequence Start**: Add external script instruction
2. **Target**: "NINA Safety Monitor"
3. **Condition**: Always run
4. **Position**: First instruction in sequence

## 🛡️ Safety Features in NINA

### What Gets Monitored:
- **NINA Process**: Ensures NINA.exe is running and responsive
- **Log Activity**: Checks for recent log entries (activity detection)
- **Weather Safety**: Real-time MQTT monitoring of ArduSafeMon
- **Sun Altitude**: Astronomical twilight calculations
- **Equipment Status**: ASCOM telescope and dome connections

### Emergency Triggers:
- NINA becomes unresponsive + Weather becomes unsafe
- Multiple safety check failures simultaneously
- Manual emergency shutdown via GUI or system tray

### Automatic Actions:
1. **Telescope**: AbortSlew() → Stop Tracking → **MANDATORY Park**
2. **Dome**: Close shutter (only after telescope is safely parked)
3. **Accessories**: Shutdown dew heaters, power management via MQTT
4. **NINA**: Terminate process if still unresponsive
5. **Alerts**: MQTT + Pushover notifications

## 📊 Monitoring Status

### Check Safety Monitor Status:
- **System Tray Icon**: Quick visual status
- **Main GUI Window**: Detailed monitoring information
- **Log Files**: `nina_safety_gui.log` for detailed history

### Normal Operation Indicators:
```
✓ MQTT Connection: Connected to 192.168.1.49
✓ Telescope Status: ASCOM.GS.Sky.Telescope Connected
✓ Dome Status: RRCI.Dome Connected  
✓ NINA Process: Running (PID: 12345)
✓ Weather Safety: Safe conditions
✓ Sun Altitude: -25.4° (Safe for observing)
```

## 🚨 Troubleshooting

### Script Won't Launch
**Check these:**
- Path is correct: `C:\Users\aegis\Documents\obsybox\nina_safetymon\nina_external_script.bat`
- Virtual environment exists: `venv\Scripts\python.exe`
- No permission issues (run NINA as administrator if needed)

### No System Tray Icon
**Possible causes:**
- Windows notification area settings hiding new icons
- Python GUI crashed (check `nina_safety_gui.log`)
- Multiple instances running (check Task Manager)

### Safety Monitor Not Responding
**Diagnostics:**
1. Check log file: `nina_safety_gui.log`
2. Verify MQTT broker connectivity: `ping 192.168.1.49`
3. Test ASCOM drivers: Run diagnostic scripts
4. Restart the external script

### Emergency Shutdown Failed
**Investigation steps:**
1. Review `emergency_shutdown.log` for detailed error messages
2. Test ASCOM connections manually
3. Verify dome hardware is operational
4. Check telescope park position manually

## 🎯 Best Practices

### Session Startup Checklist:
- [ ] Launch NINA
- [ ] Run Safety Monitor external script
- [ ] Verify system tray icon appears
- [ ] Check weather conditions manually
- [ ] Verify telescope/dome ASCOM connections
- [ ] Test emergency shutdown (optional, during daylight)

### Pre-Imaging Setup:
- [ ] Ensure Pushover notifications are working
- [ ] Verify MQTT weather sensors are online
- [ ] Check dome closure path is clear
- [ ] Confirm telescope park position is safe
- [ ] Test manual dome controls as backup

### End of Session:
- [ ] Normal NINA shutdown first
- [ ] Safety monitor continues protecting equipment
- [ ] Close safety monitor when equipment is secured
- [ ] Review logs for any warnings or errors

## 📱 Mobile Integration

### Pushover Alert Examples:

**Session Start Confirmation:**
> 🏠 Observatory: Safety Monitor Active
> 
> NINA Safety Monitor started and monitoring observatory conditions.

**Emergency Shutdown:**
> 🚨 Observatory: CRITICAL - Emergency Shutdown
> 
> NINA unresponsive during unsafe weather. Emergency shutdown initiated.
> 
> • Telescope: Parking in progress
> • Dome: Will close after telescope safe
> • Weather: Unsafe conditions detected

**Critical Issue:**
> ⚠️ Observatory: Dome Closure Failed
> 
> Telescope safely parked but dome failed to close during storm. Manual intervention required immediately!

## 🔗 Integration Benefits

### Seamless Operation:
- **One-click safety activation** from NINA
- **Background monitoring** doesn't interfere with imaging
- **Automatic emergency response** when you're not watching
- **Multi-channel alerts** ensure you're notified

### Enhanced Safety:
- **Real-time weather integration** with your existing sensors
- **ASCOM equipment control** for immediate shutdown
- **Fail-safe design** - manual intervention if automation fails
- **Comprehensive logging** for post-incident analysis

### Peace of Mind:
- **24/7 protection** even when away from observatory
- **Phone alerts** ensure immediate awareness of issues
- **Proven emergency sequences** protect expensive equipment
- **Backup systems** if primary methods fail

## 🎉 You're All Set!

Your NINA Safety Monitor is now fully integrated and ready to protect your observatory during imaging sessions. The system provides automatic monitoring with instant phone alerts, ensuring your equipment stays safe even when you're not actively watching.

**Happy imaging! 🌌**