# Simple build instructions without requiring execution policy changes

## Option 1: Use Visual Studio (Recommended if you have it)

1. Double-click `ArduSafeMon.csproj` to open in Visual Studio
2. Press **F6** or go to **Build → Build Solution**
3. Output will be in `bin\Release\net48\`

## Option 2: Use Developer Command Prompt

1. Open **Start Menu**
2. Search for **"Developer Command Prompt for VS"** or **"Developer PowerShell for VS"**
3. Navigate to driver directory:
   ```
   cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"
   ```
4. Build:
   ```
   msbuild ArduSafeMon.csproj /p:Configuration=Release
   ```

## Option 3: Install .NET SDK

If you don't have Visual Studio:

1. Download **.NET Framework 4.8 Developer Pack**: 
   https://dotnet.microsoft.com/download/dotnet-framework/net48
2. Install it
3. Reboot
4. Then run:
   ```powershell
   cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver"
   dotnet build ArduSafeMon.csproj -c Release
   ```

## After Building

The compiled DLL will be at:
```
bin\Release\net48\ASCOM.ArduSafeMon.SafetyMonitor.dll
```

## Install (Manual Method - No Scripts Needed)

1. Open **PowerShell as Administrator**
2. Navigate to the output directory:
   ```powershell
   cd "C:\Users\aegis\Documents\obsybox\ArduSafeMon\ascomDriver\bin\Release\net48"
   ```
3. Register the driver:
   ```powershell
   regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll
   ```

You should see "Types registered successfully"

## Verify Installation

1. Open **ASCOM Diagnostics** from Start Menu
2. Under SafetyMonitor section, click **Choose Device**
3. You should see **"ArduSafeMon Safety Monitor"** in the list

## Quick PowerShell Script Workaround

If you need to run the .ps1 scripts, use this method:

```powershell
# Build
powershell -ExecutionPolicy Bypass -File .\build.ps1

# Install (as Administrator)
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Or permanently allow scripts (requires Admin):
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
