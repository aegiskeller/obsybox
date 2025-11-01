# ArduSafeMon ASCOM Driver Installation Instructions

## Problem
NINA is showing error: "Retrieving the class factory for component with CLSID {A1B2C3D4-E5F6...} failed due to the following error: 80070002 The system cannot find the specified file"

This means the ASCOM driver isn't registered in Windows.

## Solution

### Step 1: Build Complete ✅
The driver has been successfully built and the DLL is available at:
`C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll`

### Step 2: Register the Driver (REQUIRED)

**You MUST run this as Administrator:**

1. **Right-click** on PowerShell or Command Prompt
2. Select **"Run as Administrator"**
3. Navigate to the driver directory:
   ```
   cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"
   ```
4. Run the registration script:
   ```
   register_driver.bat
   ```

### Alternative Manual Registration
If the batch file doesn't work, run this command as Administrator:
```
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\regasm.exe "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll" /codebase
```

### Step 3: Verify Registration
After successful registration, you should see:
- "SUCCESS: ArduSafeMon ASCOM Driver registered successfully!"
- The driver should now appear in NINA's safety monitor selection

### Step 4: Configure in NINA
1. Open NINA
2. Go to Options → Equipment → Safety Monitor
3. Look for "ASCOM.ArduSafeMon.SafetyMonitor" in the dropdown
4. Select it and click "Connect"

## Troubleshooting

### If registration fails:
- Make sure you're running as Administrator
- Make sure the DLL exists in the bin\Release folder
- Try building the project again first

### If NINA still can't find it:
- Restart NINA after registration
- Check Windows Event Viewer for COM errors
- Try unregistering and re-registering using the provided scripts

### To unregister the driver:
Run as Administrator:
```
unregister_driver.bat
```

## Files Created
- `register_driver.bat` - Register the ASCOM driver (run as Admin)
- `unregister_driver.bat` - Unregister the ASCOM driver (run as Admin)
- `bin\Release\ASCOM.ArduSafeMon.SafetyMonitor.dll` - The actual driver

## Arduino Connection
Make sure your Arduino R4 WiFi is:
1. Running the ArduSafeMon firmware
2. Connected to your network with static IP 192.168.1.99
3. Accessible via web browser at http://192.168.1.99

The ASCOM driver will communicate with the Arduino via HTTP to get safety status.