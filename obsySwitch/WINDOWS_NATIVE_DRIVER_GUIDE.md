# 🏗️ Windows Native ASCOM Driver Deployment Guide

## 🎯 Overview

Your Arduino relay controller has **TWO complete implementations**:

1. **✅ Cross-Platform Alpaca Server** (current - works on macOS/Linux/Windows)
2. **✅ Native Windows ASCOM Driver** (ready to build - Windows only)

## 🚀 Windows Native Driver Benefits

### **Automatic Discovery**
- ✅ **Appears immediately** in NINA device lists
- ✅ **No server process** to manage
- ✅ **Standard ASCOM experience** - just like ArduSafeMon
- ✅ **Faster performance** - direct serial communication

### **Professional Integration**
- ✅ **Windows Registry integration** - auto-registered
- ✅ **ASCOM Platform compliance** - full ISwitchV2 interface
- ✅ **Setup dialog** - COM port configuration GUI
- ✅ **Logging and diagnostics** - integrated with ASCOM tools

## 🛠️ Building on Windows

### **Prerequisites**
- **Windows 10/11** with .NET Framework 4.8
- **Visual Studio Community** (free) or Visual Studio Code
- **ASCOM Platform 6.6+** installed
- **Arduino IDE** for uploading firmware

### **Step 1: Install Dependencies**

```powershell
# Install Visual Studio Community (if not already installed)
# Download from: https://visualstudio.microsoft.com/vs/community/

# Install ASCOM Platform
# Download from: https://ascom-standards.org/Downloads/Index.htm

# Install .NET Framework 4.8 (usually pre-installed on Windows 10/11)
```

### **Step 2: Copy Project Files**

```powershell
# Copy the entire obsybox project to Windows
# Transfer via git clone, USB drive, or network share
git clone https://github.com/aegiskeller/obsybox.git
cd obsybox\\obsySwitch\\ascomDriver
```

### **Step 3: Restore NuGet Packages**

```powershell
# In the ascomDriver directory
dotnet restore ObsyBoxRelaySwitch.csproj
# OR open in Visual Studio and it will auto-restore
```

### **Step 4: Build the Driver**

#### **Option A: Visual Studio (Recommended)**
1. **Open** `ObsyBoxRelaySwitch.csproj` in Visual Studio
2. **Build** → **Build Solution** (Ctrl+Shift+B)
3. **Build** → **Rebuild Solution** (for clean build)

#### **Option B: Command Line**
```powershell
# Build Release version
dotnet build ObsyBoxRelaySwitch.csproj -c Release

# OR using MSBuild
msbuild ObsyBoxRelaySwitch.csproj /p:Configuration=Release
```

### **Step 5: Register the Driver**

```powershell
# Navigate to build output
cd bin\\Release

# Register the driver with Windows (run as Administrator)
regasm ASCOM.ObsyBox.RelaySwitch.dll /tlb /codebase

# Verify registration
reg query "HKEY_LOCAL_MACHINE\\SOFTWARE\\ASCOM\\Switch Drivers\\ASCOM.ObsyBox.RelaySwitch"
```

## 🎮 Using the Native Driver in NINA

### **Automatic Discovery**
1. **Open NINA**
2. **Equipment** → **Switch**
3. **Gear icon ⚙️** → **ASCOM Switch**
4. **Choose ASCOM Switch** → **"ObsyBox Relay Switch"** appears in list!
5. **Select** and **Connect**

### **Setup Dialog**
- **COM Port**: Auto-detects Arduino ports
- **Baud Rate**: 9600 (matches Arduino firmware)
- **Timeout**: 5000ms (5 seconds)
- **Test Connection**: Button to verify Arduino communication

### **Switch Names**
- **Switch 0**: Mount (Pin 2)
- **Switch 1**: Camera (Pin 3)  
- **Switch 2**: Focuser (Pin 4)
- **Switch 3**: Aux (Pin 5)

## 🔧 Driver Features

### **Complete ASCOM ISwitchV2 Implementation**
```csharp
// Your driver implements all required properties:
public bool Connected { get; set; }          // Connection management
public string Description { get; }           // Device description  
public string DriverInfo { get; }           // Driver information
public string DriverVersion { get; }        // Version info
public string Name { get; }                 // Device name
public short MaxSwitch { get; }             // Number of switches (3, 0-based)
public bool CanWrite(short id)              // Switch writability
public bool GetSwitch(short id)             // Get switch state
public void SetSwitch(short id, bool state) // Set switch state
public string GetSwitchName(short id)       // Get switch name
public string GetSwitchDescription(short id) // Get switch description
```

### **Arduino Communication Protocol**
```json
// Commands sent to Arduino:
{"command": "get_status"}
{"command": "set_relay", "relay": 0, "state": true}
{"command": "get_relay", "relay": 0}

// Responses from Arduino:
{"success": true, "relays": [...]}
{"success": true, "state": true}
```

### **Error Handling and Logging**
- ✅ **ASCOM exceptions** with proper error codes
- ✅ **Trace logging** to ASCOM log files
- ✅ **Serial port** connection management
- ✅ **Timeout handling** for Arduino communication

## 📊 Performance Comparison

| Feature | Alpaca Server | Native ASCOM |
|---------|---------------|--------------|
| **Platform** | Cross-platform | Windows only |
| **Discovery** | Manual setup | Automatic |
| **Performance** | HTTP overhead | Direct serial |
| **Setup** | Server process | One-click install |
| **Maintenance** | Manual restart | Self-managing |
| **NINA Integration** | Manual URL entry | Auto-detected |

## 🔄 Deployment Strategy

### **Recommended Approach**
1. **Development**: Use Alpaca on macOS (current setup)
2. **Production**: Deploy native ASCOM on Windows observatory PC

### **Hybrid Setup** 
```
Development Mac: ✅ Alpaca Server (testing/development)
Observatory PC:  ✅ Native ASCOM (production/NINA)
Remote Access:   ✅ Alpaca Server (network control)
```

## 📦 Installation Package

You could create an installer:

```xml
<!-- WiX Installer Project -->
<Product Id="*" Name="ObsyBox Relay Switch ASCOM Driver" 
         Language="1033" Version="1.0.0.0" 
         Manufacturer="ObsyBox Project">
  
  <Package InstallerVersion="200" Compressed="yes" 
           InstallScope="perMachine" />
           
  <MajorUpgrade DowngradeErrorMessage="A newer version is already installed." />
  
  <MediaTemplate EmbedCab="yes" />
  
  <!-- Install driver DLL and register with ASCOM -->
  <ComponentGroup Id="DriverFiles">
    <Component Directory="INSTALLFOLDER">
      <File Source="ASCOM.ObsyBox.RelaySwitch.dll" />
      <RegistryValue Root="HKLM" 
                     Key="SOFTWARE\\ASCOM\\Switch Drivers\\ASCOM.ObsyBox.RelaySwitch"
                     Name="Description" Value="ObsyBox Arduino Relay Switch" 
                     Type="string" />
    </Component>
  </ComponentGroup>
</Product>
```

## 🎯 Next Steps

### **For Windows Deployment**:
1. **Transfer project** to Windows machine
2. **Build in Visual Studio** 
3. **Register driver** with `regasm`
4. **Test in NINA** - should appear automatically
5. **Create installer** for easy distribution

### **For Continued macOS Development**:
- Keep using Alpaca server approach
- All testing and development can continue on macOS
- Deploy to Windows when ready for production

**Result**: Your Arduino relay switch becomes a **first-class ASCOM device** on Windows, appearing automatically in NINA just like professional observatory equipment!

Would you like me to help you build and test this on a Windows machine?