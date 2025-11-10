# 🚀 ObsyBox ASCOM Auto-Service Setup

## Problem Solved: Automatic ASCOM Switch Discovery

This guide sets up your Arduino relay switch to **automatically appear in NINA** without manual server starting.

## 🎯 What This Does

- **Arduino Detection**: Monitors for Arduino connection
- **Auto Server Start**: Launches ASCOM server when Arduino detected  
- **Health Monitoring**: Restarts if server crashes
- **Clean Shutdown**: Stops server when Arduino disconnected
- **Boot Integration**: Starts automatically with macOS

## 📦 Installation Steps

### Step 1: Test the Auto-Service

```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch

# Test the auto-service manually
python obsybox_auto_service.py
```

You should see:
```
🔧 ObsyBox ASCOM Auto-Service Starting
📱 Monitoring for Arduino connection...
✅ Arduino detected - starting ASCOM server
🚀 ASCOM Alpaca server started
```

### Step 2: Install as macOS Service

```bash
# Copy the launch agent to macOS LaunchAgents
cp com.obsybox.ascom.autoservice.plist ~/Library/LaunchAgents/

# Load the service (starts immediately and on boot)
launchctl load ~/Library/LaunchAgents/com.obsybox.ascom.autoservice.plist

# Check service status
launchctl list | grep obsybox
```

### Step 3: Verify Auto-Operation

1. **Unplug Arduino** - Service should detect disconnection
2. **Plug in Arduino** - Service should auto-start ASCOM server
3. **Open NINA** - Switch should appear automatically in Equipment

## 🎮 NINA Usage (Now Automatic!)

### Equipment Setup (One-Time)
1. **Equipment** → **Switch** → **Gear icon ⚙️**
2. **ASCOM Switch** → **Choose ASCOM Switch**
3. **Alpaca Discovery** → Enter: `http://localhost:11111`
4. Select: **"ObsyBox Relay Switch"**

### Daily Operation
1. **Plug in Arduino** → Service auto-starts server
2. **Open NINA** → Switch automatically available
3. **Use normally** → No manual server management needed!

## 🔧 Service Management

### Check Service Status
```bash
# See if service is running
launchctl list com.obsybox.ascom.autoservice

# View service logs
tail -f ~/Documents/Arduino/obsybox/obsySwitch/autoservice.log
```

### Stop Service
```bash
# Stop and unload service
launchctl unload ~/Library/LaunchAgents/com.obsybox.ascom.autoservice.plist
```

### Restart Service
```bash
# Restart service
launchctl unload ~/Library/LaunchAgents/com.obsybox.ascom.autoservice.plist
launchctl load ~/Library/LaunchAgents/com.obsybox.ascom.autoservice.plist
```

## 🔍 How It Works

### Service Flow
1. **Boot** → macOS loads `com.obsybox.ascom.autoservice`
2. **Monitor** → Service checks for Arduino every 5 seconds
3. **Detect** → Arduino plugged in
4. **Start** → `alpaca_switch_server.py` launched automatically
5. **Available** → NINA sees switch at `http://localhost:11111`
6. **Disconnect** → Arduino unplugged
7. **Stop** → Server automatically stopped

### Arduino States
- **Connected**: ✅ Auto-starts ASCOM server
- **Disconnected**: ❌ Auto-stops ASCOM server  
- **Reconnected**: 🔄 Auto-restarts ASCOM server

## 📋 Troubleshooting

### Service Not Starting
```bash
# Check service exists
ls ~/Library/LaunchAgents/com.obsybox.ascom.autoservice.plist

# Check for errors
tail ~/Documents/Arduino/obsybox/obsySwitch/autoservice_error.log

# Manually test
python obsybox_auto_service.py
```

### Arduino Not Detected
- ✅ Check USB cable connection
- ✅ Verify Arduino has `RelayController_Serial.ino` loaded
- ✅ Close Arduino IDE Serial Monitor if open

### NINA Can't Find Switch
- ✅ Check service is running: `launchctl list | grep obsybox`
- ✅ Verify server responds: `curl http://localhost:11111/status`
- ✅ Check NINA Equipment → Switch → ASCOM Switch setup

## 🎯 Result

**Before**: Manual `python alpaca_switch_server.py` every time
**After**: Plug in Arduino → Switch automatically appears in NINA!

Your ObsyBox relay switch now behaves exactly like ArduSafeMon - automatically available in NINA when hardware is connected.

## 🔄 Integration with Existing ObsyBox

This auto-service integrates perfectly with:
- **ArduSafeMon**: Weather safety monitoring
- **NINA Scheduling**: Target selector and sequences
- **Dew Heater**: Environmental control
- **Monitor Cam**: AllSky imaging

All components can now start automatically when their respective hardware is detected.

---

🚀 **Auto-Discovery Problem Solved!** Your Arduino switch now appears in NINA just like any professional ASCOM device.