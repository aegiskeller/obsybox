# Quick Start Guide - ArduSafeMon ASCOM Driver

## Prerequisites Checklist

- [ ] ASCOM Platform 6.6+ installed ([Download](https://ascom-standards.org/Downloads/Index.htm))
- [ ] Arduino with ArduSafeMon firmware connected via USB
- [ ] Know your Arduino's COM port (check Device Manager)
- [ ] Visual Studio 2019/2022 OR .NET Framework 4.8 SDK

## Build and Install (5 minutes)

### Step 1: Build the Driver

Open PowerShell in this directory:

```powershell
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"

# If you get "scripts is disabled" error, use one of these methods:

# Method 1: Bypass execution policy for this session
powershell -ExecutionPolicy Bypass -File .\build.ps1

# Method 2: Run the build command directly
dotnet build ArduSafeMon.csproj -c Release

# Method 3: Use the batch file instead
.\build.bat
```

### Step 2: Install the Driver

**Important: Run PowerShell as Administrator**

```powershell
# Navigate to the build output
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release"

# Register the driver (use 64-bit regasm for ASCOM compatibility)
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
```

You should see "Driver installed successfully!"

## Configure and Test

### Step 3: Configure COM Port

1. Open **ASCOM Diagnostics** from Start Menu
2. Click **Choose Device** under SafetyMonitor section
3. Select **ArduSafeMon Safety Monitor**
4. Click **Properties**
5. Select your Arduino's COM port from dropdown
6. Click **OK**

### Step 4: Test Connection

In ASCOM Diagnostics:
1. Click **Connect**
2. Click **Read IsSafe** button
3. Should show **True** or **False** based on weather conditions

### Step 5: Use with NINA

1. Open NINA
2. Go to **Options → Equipment → Safety Monitor**
3. Click **Choose...**
4. Select **ArduSafeMon Safety Monitor**
5. Click **Connect**
6. Status appears in NINA equipment panel

## Troubleshooting Quick Fixes

**Driver doesn't appear in ASCOM Chooser**
```powershell
# Run as Administrator
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release"
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
```

**"Cannot connect to COM port"**
- Close Arduino IDE (it locks the port!)
- Check Device Manager for correct COM port
- Try unplugging/replugging Arduino USB cable

**"Timeout reading from Arduino"**
- Open Arduino Serial Monitor
- Type `S#` and press Enter
- Should see `safe#` or `notsafe#`
- If not, re-upload ArduSafeMon firmware

**Serial port stuck after disconnect**
- Close NINA completely
- Device Manager → Ports → Disable/Enable Arduino port
- Or reboot Windows

## Enable Debug Logging

1. In driver setup, check "Trace on"
2. Logs saved to: `C:\Users\<username>\Documents\ASCOM\Logs\ArduSafeMon.log`
3. View in real-time:

```powershell
Get-Content "$env:USERPROFILE\Documents\ASCOM\Logs\ArduSafeMon.log" -Wait -Tail 20
```

## Uninstall

```powershell
# Run as Administrator
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"
.\install.ps1 -Uninstall
```

## Need More Help?

See full README.md for detailed documentation and troubleshooting.
