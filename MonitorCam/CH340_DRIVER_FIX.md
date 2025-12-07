# CH340 Driver Management Guide for ESP32-CAM

## The Problem
AI Thinker ESP32-CAM boards use clone CH340/CH343 USB-to-serial chips that require the **older 2014 driver** (version 3.4.2014.8, dated 08/08/2014). Windows Update automatically installs newer drivers that don't work properly with these clone chips, causing upload failures.

## Quick Fix Steps

### 1. Run the Auto-Update Blocker Script (As Administrator)
```powershell
# Right-click PowerShell and select "Run as Administrator"
cd C:\Users\Admin\Documents\Arduino\obsybox\MonitorCam
.\disable_ch340_auto_update.ps1
```

This script will:
- Find all CH340 devices
- Add them to Windows Update exclusion list
- Disable automatic driver downloads globally
- Protect existing driver from being replaced

### 2. Download the Correct Driver
**Official WCH Driver (2014 version):**
- Direct link: http://www.wch.cn/downloads/CH341SER_ZIP.html
- Look for: **CH341SER.EXE** dated **08/08/2014**
- Version: **3.4.2014.8**

**Alternative sources if official link doesn't work:**
- Search for "CH340 driver 3.4.2014.8"
- Arduino community forums often have mirrors
- Check ESP32-CAM specific forums

### 3. Install the 2014 Driver

**Uninstall Current Driver:**
1. Open **Device Manager** (`devmgmt.msc`)
2. Expand **Ports (COM & LPT)**
3. Find **USB-SERIAL CH340** devices
4. Right-click → **Uninstall device**
5. ☑️ Check "Delete the driver software for this device"
6. Click **Uninstall**
7. Repeat for all CH340 devices

**Install Old Driver:**
1. Disconnect ESP32-CAM
2. Run **CH341SER.EXE** (2014 version)
3. Click **INSTALL**
4. Wait for "Driver install success" message
5. Connect ESP32-CAM
6. Verify in Device Manager - should show COM port

**Verify Driver Version:**
1. Device Manager → USB-SERIAL CH340
2. Right-click → **Properties**
3. **Driver** tab → **Driver Details**
4. Should show: **C:\Windows\System32\drivers\ch341.sys**
5. Version should be: **3.4.2014.8**
6. Date should be: **8/8/2014**

### 4. Additional Protection (Optional but Recommended)

**Group Policy Method (Windows Pro/Enterprise):**
```
1. Win+R → gpedit.msc
2. Computer Configuration → Administrative Templates → Windows Components → Windows Update
3. "Do not include drivers with Windows Updates" → Enabled
```

**Registry Method (All Windows versions):**
Already handled by the PowerShell script above, but you can verify:
```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching
  SearchOrderConfig = 0 (DWORD)

HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions
  DenyDeviceIDs = 1 (DWORD)
  DenyDeviceIDsRetroactive = 1 (DWORD)
```

## Troubleshooting

### Driver Keeps Getting Updated
1. Check Windows Update settings:
   - Settings → Update & Security → Advanced options
   - Turn OFF "Receive updates for other Microsoft products"
   
2. Pause Windows Update temporarily during development:
   - Settings → Update & Security → Pause updates for 7 days

3. Use Show or Hide Updates tool:
   - Download from Microsoft: wushowhide.diagcab
   - Hide specific driver updates

### Upload Still Fails After Driver Install
1. **Check hardware boot mode:**
   - GPIO 0 MUST be connected to GND during upload
   - Press RESET button after connecting GPIO 0 to GND
   - Remove GPIO 0 jumper after upload completes

2. **Try different upload speed:**
   - Arduino IDE → Tools → Upload Speed
   - Try: 115200 (most reliable)
   - If fails, try: 460800 or 921600

3. **Check power supply:**
   - ESP32-CAM draws significant current during WiFi/camera
   - USB might be insufficient - use external 5V power supply
   - Common issue: Brown-out during upload

4. **Close Serial Monitor:**
   - Serial Monitor locks the COM port
   - Must be closed before upload

## USB-to-Serial Adapter Compatibility

If still having issues, the problem might be the USB-to-serial adapter:

**Known Working Adapters:**
- ✅ CP2102 (best compatibility)
- ✅ FT232RL (FTDI genuine)
- ⚠️ CH340G (needs 2014 driver)
- ❌ PL2303 (often problematic)

**AI Thinker boards typically use:**
- Clone CH340/CH343 chips
- Require specific driver version
- May have label "USB-SERIAL CH340" or "CH343"

## Quick Reference Commands

**Check connected CH340 devices:**
```powershell
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*CH340*" } | Select-Object FriendlyName, Status, InstanceId
```

**Kill stuck serial processes:**
```powershell
Stop-Process -Name "serial-discovery" -Force -ErrorAction SilentlyContinue
```

**List all COM ports:**
```powershell
[System.IO.Ports.SerialPort]::GetPortNames()
```

## Prevention Best Practices

1. **After successful driver install:**
   - Create a system restore point
   - Backup the driver files to cloud storage
   - Document your working COM port number

2. **Before major Windows updates:**
   - Export your working driver from Device Manager
   - Backup → Driver → Export
   - Re-install after update if needed

3. **Use dedicated development machine:**
   - Consider keeping a PC with working drivers offline
   - Or use Linux/macOS (no driver issues with CH340)

## Alternative: Arduino CLI (More Reliable)

The project uses `bin\arduino-cli` which can be more stable:

```powershell
# From obsybox directory
.\bin\arduino-cli compile --fqbn esp32:esp32:esp32cam MonitorCam\ESP32_Production
.\bin\arduino-cli upload --fqbn esp32:esp32:esp32cam --port COM11 MonitorCam\ESP32_Production
```

Arduino CLI doesn't hold ports open like the IDE, reducing conflicts.

---

**Last Updated:** December 2025  
**Tested On:** Windows 10/11 with AI Thinker ESP32-CAM  
**Project:** ObsyBox Observatory Monitor Camera
