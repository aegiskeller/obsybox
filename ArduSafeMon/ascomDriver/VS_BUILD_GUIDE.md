# Visual Studio Installation & Build Guide

## Visual Studio Installation Checklist

When the installer asks what to install, make sure to select:

✅ **.NET desktop development** workload
   - This includes everything needed to build ASCOM drivers
   - Includes MSBuild, C# compiler, and .NET Framework targets

### Optional but Useful:
- **Desktop development with C++** (if you want to modify Arduino code)
- **.NET Framework 4.8 targeting pack** (should be included with desktop development)

## After Visual Studio Installs

### Quick Build Steps:

1. **Open the Project**
   ```
   Double-click: C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\ArduSafeMon.csproj
   ```
   Visual Studio will open automatically

2. **Restore NuGet Packages**
   - Visual Studio should automatically restore packages
   - If not, right-click solution → "Restore NuGet Packages"
   - Wait for status bar to show "Ready"

3. **Build**
   - Press **F6** (or Build → Build Solution)
   - Watch the Output window (View → Output)
   - Should see: "Build succeeded"

4. **Locate Output DLL**
   ```
   File Explorer → bin\Release\net48\ASCOM.ArduSafeMon.SafetyMonitor.dll
   ```

### Then Install the Driver

Open **PowerShell as Administrator**:

```powershell
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release\net48"
regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
```

Should see: "Types registered successfully"

## Using Developer PowerShell (Alternative)

After VS installs, you can use **Developer PowerShell for VS**:

1. Open Start Menu
2. Search for **"Developer PowerShell for VS 2022"**
3. Navigate to driver folder:
   ```powershell
   cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"
   ```
4. Now the scripts will work:
   ```powershell
   .\build.ps1
   # Then as Admin:
   .\install.ps1
   ```

## Troubleshooting Build Issues

### "Could not find a part of the path"
- Right-click solution → Properties → Check target framework is .NET Framework 4.8

### "NuGet packages failed to restore"
- Tools → NuGet Package Manager → Package Manager Console
- Run: `Update-Package -reinstall`

### "ASCOM references not found"
- Make sure ASCOM Platform 6.6+ is installed
- Download from: https://ascom-standards.org/Downloads/Index.htm

### Build succeeded but DLL is missing
- Check: `bin\Release\net48\` folder
- If empty, try Build → Rebuild Solution

## First Build Checklist

After VS finishes installing:

- [ ] Open `ArduSafeMon.csproj`
- [ ] Wait for NuGet package restore (bottom status bar)
- [ ] Press F6 to build
- [ ] Check Output window shows "Build succeeded"
- [ ] Verify DLL exists in `bin\Release\net48\`
- [ ] Run regasm as Administrator to register
- [ ] Test in ASCOM Diagnostics
- [ ] Connect from NINA

## Quick Reference Commands

**Build from Visual Studio:**
- Open project, press F6

**Build from Developer PowerShell:**
```powershell
cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"
msbuild ArduSafeMon.csproj /p:Configuration=Release
```

**Install (as Administrator):**
```powershell
cd bin\Release\net48
regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
```

**Verify Installation:**
- Open ASCOM Diagnostics
- SafetyMonitor tab → Choose Device
- Look for "ArduSafeMon Safety Monitor"

---

## While You Wait...

Make sure you have these ready:
1. ✅ ASCOM Platform 6.6+ installed?
2. ✅ Arduino connected via USB?
3. ✅ Know which COM port? (Check Device Manager)
4. ✅ Arduino running ArduSafeMon firmware?

Test Arduino communication now:
1. Open Arduino IDE Serial Monitor (9600 baud)
2. Type: `S#` and press Enter
3. Should see: `safe#` or `notsafe#`

If that works, the driver will work too! 🎉
