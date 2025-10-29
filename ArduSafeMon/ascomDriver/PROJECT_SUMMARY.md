# ArduSafeMon ASCOM Driver - Project Summary

## What Was Created

A complete ASCOM SafetyMonitor driver for ArduSafeMon that uses **serial communication** to integrate with NINA and other ASCOM-compatible astronomy software.

## Architecture

**Communication Flow:**
```
NINA/ASCOM App → ASCOM Driver → Serial (COM port) → Arduino R4 WiFi
                                       ↓
                                  Send: S#
                                       ↓
                           Receive: safe# or notsafe#
```

## Files Created

### Core Driver Files
- **Driver.cs** - Main ASCOM ISafetyMonitorV3 implementation with serial communication
- **SetupDialogForm.cs/.Designer.cs** - Windows Forms configuration UI for COM port selection
- **AssemblyInfo.cs** - Assembly metadata and COM registration GUIDs
- **ArduSafeMon.csproj** - .NET Framework 4.8 project file with ASCOM dependencies

### Build & Install
- **build.ps1** - PowerShell build script (preferred)
- **build.bat** - Batch file build script (alternative)
- **install.ps1** - Administrator installation script with regasm automation
- **App.config** - .NET runtime configuration

### Resources
- **Properties/Resources.Designer.cs** - Resource manager for embedded assets
- **Properties/Resources.resx** - Resource XML (references ASCOM logo)
- **Resources/ASCOM_LOGO_PLACEHOLDER.txt** - Instructions for adding ASCOM logo

### Documentation
- **README.md** - Complete documentation (requirements, build, install, troubleshooting)
- **QUICKSTART.md** - 5-minute setup guide for immediate use

## Key Features

### ASCOM Implementation
- ✅ ISafetyMonitorV3 interface
- ✅ IsSafe property with automatic refresh (5-second cache)
- ✅ COM registration for Windows interop
- ✅ ASCOM Profile persistence for settings

### Serial Communication
- ✅ Robust SerialPort handling (9600 baud, 8N1)
- ✅ 2-second timeout with error handling
- ✅ Automatic flush of debug output from Arduino
- ✅ Connection state management

### User Interface
- ✅ Setup dialog with COM port dropdown
- ✅ Auto-detection of available COM ports
- ✅ Trace logging toggle
- ✅ Professional Windows Forms UI

### Error Handling
- ✅ Connection failures
- ✅ Serial port timeouts
- ✅ Unexpected responses
- ✅ Port busy/unavailable conditions
- ✅ ASCOM-compliant exceptions

## How It Works

### 1. Installation Flow
```powershell
# Build
.\build.ps1

# Install (as Admin)
.\install.ps1

# Result: Driver registered in Windows COM, visible in ASCOM Chooser
```

### 2. Configuration
- User opens ASCOM setup dialog
- Selects Arduino COM port from dropdown
- Settings saved to ASCOM Profile

### 3. Runtime Operation
```
NINA queries IsSafe every few seconds
  ↓
Driver checks if cached status > 5 seconds old
  ↓
If stale: Send "S#" to Arduino via serial
  ↓
Read response: "safe#" or "notsafe#"
  ↓
Parse and cache status + timestamp
  ↓
Return boolean to NINA
```

### 4. Arduino Firmware Compatibility
Your existing Arduino code already implements the protocol:
```cpp
if (Serial.available()) {
    String cmd = Serial.readStringUntil('#');
    if (cmd == "S") {
        if (medianSafe) {
            Serial.print("safe#");
        } else {
            Serial.print("notsafe#");
        }
        // Debug output follows (driver automatically discards this)
    }
}
```

## NINA Integration

Once installed and configured:

1. **Safety Monitoring**: NINA automatically polls safety status
2. **Unsafe Actions**: When unsafe detected, NINA can:
   - Park telescope
   - Close dome/roof  
   - Pause sequence
   - Warm camera
3. **Recovery**: When safe again, NINA can resume operations

Configure these behaviors in: **NINA → Options → Safety → Safety Monitor Settings**

## Advantages of Serial vs MQTT

| Feature | Serial | MQTT |
|---------|--------|------|
| Latency | ~100ms | Variable (network dependent) |
| Reliability | Direct connection | Broker dependency |
| ASCOM Pattern | Standard | Non-standard |
| Setup Complexity | Plug USB, select port | Configure broker, network, credentials |
| Windows Integration | Native SerialPort | Requires MQTT library |
| Error Handling | Clear, immediate | Network issues unclear |

## Testing Checklist

- [ ] Build completes without errors
- [ ] Driver appears in ASCOM Diagnostics
- [ ] COM port selection works in setup dialog
- [ ] Connection succeeds to Arduino
- [ ] IsSafe returns correct status (test both safe/unsafe)
- [ ] NINA recognizes driver
- [ ] NINA shows correct status in equipment panel
- [ ] Unsafe condition triggers NINA safety actions
- [ ] Trace logging works when enabled

## Troubleshooting Reference

| Issue | Solution |
|-------|----------|
| Driver not in ASCOM Chooser | Run `regasm /codebase` as Admin |
| Can't connect to COM port | Close Arduino IDE, check Device Manager |
| Timeout reading Arduino | Test with Serial Monitor: `S#` → `safe#` |
| Port held after disconnect | Disable/Enable port in Device Manager |
| Wrong status reported | Check Arduino web UI, enable driver trace logging |

## Next Steps

1. **Build the driver**: Run `.\build.ps1`
2. **Install**: Run `.\install.ps1` as Administrator
3. **Configure**: Set COM port in ASCOM setup dialog
4. **Test**: Use ASCOM Diagnostics to verify
5. **Integrate**: Connect from NINA and configure safety actions

## File Locations Summary

```
obsybox/ArduSafeMon/ascomDriver/
├── Driver.cs                          # Main driver logic
├── SetupDialogForm.cs                 # Config UI code
├── SetupDialogForm.Designer.cs        # Config UI designer
├── ArduSafeMon.csproj                 # Project file
├── AssemblyInfo.cs                    # Version & COM GUID
├── App.config                         # Runtime config
├── build.ps1                          # Build script
├── install.ps1                        # Install script
├── README.md                          # Full documentation
├── QUICKSTART.md                      # Quick setup guide
├── Properties/
│   ├── Resources.Designer.cs          # Resource manager
│   └── Resources.resx                 # Resource XML
└── Resources/
    └── ASCOM_LOGO_PLACEHOLDER.txt     # Logo reminder

After build:
├── bin/Release/net48/
│   └── ASCOM.ArduSafeMon.SafetyMonitor.dll   # Final DLL
```

## Support & Documentation

- **Full docs**: See README.md in this directory
- **Quick start**: See QUICKSTART.md
- **Arduino firmware**: `../ArduSafeMon_R4wifi_weather/ArduSafeMon_R4wifi/`
- **ASCOM Platform**: https://ascom-standards.org/
- **Repository**: https://github.com/aegiskeller/obsybox
