# ObsyBox Monitor Camera

ESP32-CAM based monitoring system for the ObsyBox observatory with dark theme interface, system health monitoring, and idle-safe watchdog protection.

## � **Clear Directory Structure**

```
MonitorCam/
├── README.md                    # 📖 This overview document
├── ESP32_Development/           # 🔧 DEVELOPMENT: Access Point mode
│   ├── ESP32_Development.ino    # Development sketch (AP mode)
│   └── camera_pins.h            # AI Thinker pin definitions
├── ESP32_Production/            # 🚀 PRODUCTION: Station mode  
│   ├── ESP32_Production.ino     # Production sketch (WiFi client)
│   ├── camera_pins.h            # AI Thinker pin definitions
│   ├── arduino_secrets.h        # WiFi credentials (configure before deploy)
│   └── README_DEPLOY.md         # Complete deployment guide
└── archive/                     # 📦 Historical & testing versions
    ├── DEVELOPMENT_NOTES.md     # Hardware issues & dev history
    ├── ESP32_Debug_Testing/     # Debug version from troubleshooting
    ├── CameraWebServer/         # Original Arduino examples + iterations
    └── ESP32_Mobile_Clean/      # Previous mobile version (had issues)
```

## 🎯 **Which Version Should I Use?**

### 🔧 **ESP32_Development** - Choose this for:
- **Testing new features** before deployment
- **Portable setup** without existing WiFi  
- **Development work** and experimentation
- **Demonstrations** where you control the network
- **Backup access** when main network is down

**Access**: Creates `ESP32-CAM-AP` network → Connect → `http://192.168.4.1`

### 🚀 **ESP32_Production** - Choose this for:
- **Observatory deployment** to existing network
- **Permanent installation** in ObsyBox system  
- **Network integration** with other devices
- **Remote access** from anywhere on network
- **Automation integration** with fixed IP

**Access**: Connects to your WiFi → Check router/serial for IP → `http://[assigned-ip]`

## ⚡ **Features (Both Versions)**
- **Dark Cyberpunk Theme**: High-contrast green-on-black interface
- **Fast Camera Controls**: Capture, streaming (500ms), LED toggle, fast refresh
- **Health Monitoring**: Real-time system diagnostics with JSON API
- **Smart Watchdog**: Idle-safe protection with auto-recovery
- **Mobile Compatible**: Works on iPhone Safari and desktop browsers
- **Speed Optimized**: VGA resolution for responsive performance

## 🚀 **Quick Start**

### Development Version (AP Mode)
```bash
# Upload to ESP32-CAM
arduino-cli upload --fqbn esp32:esp32:esp32cam --port /dev/cu.usbserial-XXXX MonitorCam/ESP32_Development

# Connect to WiFi network: ESP32-CAM-AP
# Navigate to: http://192.168.4.1
```

### Production Version (Station Mode)  
```bash
# 1. Configure WiFi credentials
nano MonitorCam/ESP32_Production/arduino_secrets.h

# 2. Upload to ESP32-CAM
arduino-cli upload --fqbn esp32:esp32:esp32cam --port /dev/cu.usbserial-XXXX MonitorCam/ESP32_Production

# 3. Check serial monitor for assigned IP
# 4. Navigate to: http://[assigned-ip]
```

## 🔧 **Hardware Requirements**
- **Board**: AI Thinker ESP32-CAM (`esp32:esp32:esp32cam`)
- **Upload Speed**: 115200 baud
- **Camera**: OV2640 with PSRAM support
- **LED**: GPIO 4 flash control

## 🌐 **API Endpoints (Both Versions)**
- `/` - Main camera interface  
- `/capture` - Single photo capture
- `/stream` - Timer-based streaming
- `/led` - Toggle flash LED  
- `/health` - System diagnostics (JSON)

## 🎯 **Observatory Integration**
Perfect for ObsyBox automated observatory system:
- **AllSky Monitoring**: Visual sky condition assessment
- **Security Monitoring**: Equipment and enclosure oversight  
- **Weather Verification**: Visual confirmation of sensor readings
- **Remote Diagnostics**: Check system status from anywhere

---

**💡 Tip**: Start with Development version for testing, then switch to Production for deployment!

*Last updated: November 2025 - ObsyBox Observatory Project* 🔭

### Board Configuration
- **Board**: AI Thinker ESP32-CAM (`esp32:esp32:esp32cam`)
- **Upload Speed**: 115200 baud
- **Flash LED**: GPIO 4
- **Camera Module**: OV2640 with PSRAM

### Pin Configuration
Uses standard AI Thinker ESP32-CAM pin mapping (see `camera_pins.h`)

## 📊 System Monitoring

### Health Check Features
- **Real-time Status**: System health, uptime, memory usage
- **Request Tracking**: Monitors web interface activity
- **Error Detection**: Camera failures, low memory alerts
- **Auto-Recovery**: Resets on true system failures only

### Watchdog Protection
- **Smart Detection**: Distinguishes between idle vs. unresponsive
- **Function Testing**: Tests WiFi, memory, and timer systems
- **Observatory-Ready**: Safe for long idle periods between observations

## 🌐 Web Interface

### Available Endpoints
- `/` - Main camera interface
- `/capture` - Take single photo
- `/stream` - Timer-based image streaming
- `/led` - Toggle flash LED
- `/health` - System diagnostics (JSON)

### Interface Controls
- **Capture**: Single photo with timestamp
- **Start/Stop Stream**: 1-second refresh streaming
- **Toggle LED**: Flash LED control
- **System Health**: Real-time diagnostics

## 📁 Archive

**`archive/`** contains older development versions:
- `CameraWebServer/` - Original Arduino examples and iterations
- `ESP32_Mobile_Clean/` - Previous mobile-optimized version (had buffer overflow issues)

## 🔍 Troubleshooting

### Common Issues
- **Upload Fails**: Check if serial monitor is open, may need to close it
- **Camera Not Working**: Verify GPIO 4 LED configuration and PSRAM
- **WiFi Issues**: Look for `ESP32-CAM-AP` network, may take 30s to appear
- **Page Won't Load**: Ensure connected to camera's AP, try `192.168.4.1`

### Serial Monitor Debug
Connect at 115200 baud to see:
- Boot sequence and camera initialization
- System health status every 30 seconds
- Request activity and error logging
- Memory and uptime statistics

## 🎯 Integration Notes

Part of the larger ObsyBox observatory automation system. This camera provides:
- **AllSky Monitoring**: Visual sky conditions
- **Security Monitoring**: Equipment and enclosure oversight  
- **Weather Verification**: Visual confirmation of sensor data
- **Remote Access**: Monitor observatory status from anywhere

---

*Last updated: November 2025*
*For ObsyBox observatory automation project*