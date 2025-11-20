# ESP32-S3 Freenove WROOM Camera Firmware

ObsyBox AllSky Monitor Camera adapted for **ESP32-S3 Freenove WROOM** development board.

## Hardware Specifications

### ESP32-S3 Freenove WROOM Features
- **MCU**: ESP32-S3-WROOM-1 (Dual-core Xtensa LX7 @ 240MHz)
- **RAM**: 512KB SRAM + 2MB/8MB PSRAM (QSPI)
- **Flash**: 4MB/8MB/16MB
- **WiFi**: 802.11 b/g/n (2.4 GHz)
- **Camera**: OV2640 2MP sensor
- **LED**: GPIO 48 (onboard RGB LED)

### Pin Configuration
Camera pins are defined in `camera_pins.h`:
- XCLK: GPIO 15
- SIOD (SDA): GPIO 4
- SIOC (SCL): GPIO 5
- Data pins: Y2-Y9 on GPIOs 11,9,8,10,12,18,17,16
- VSYNC: GPIO 6
- HREF: GPIO 7
- PCLK: GPIO 13
- LED: GPIO 48

## Network Configuration

### Static IP Setup
Default configuration in code (change as needed):
```cpp
IPAddress local_IP(192, 168, 1, 149);  // Change this!
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);
```

### WiFi Credentials
Edit `arduino_secrets.h`:
```cpp
#define SECRET_SSID "YourNetworkName"
#define SECRET_PASS "YourPassword"
```

## ESP32-S3 Improvements Over Original ESP32

### Performance Enhancements
1. **Higher Resolution**: UXGA (1600x1200) vs SVGA (800x600)
2. **Better Image Quality**: JPEG quality 10 vs 12
3. **More Memory**: 20KB heap threshold vs 10KB
4. **PSRAM Reporting**: Added `getFreePsram()` monitoring
5. **Advanced Sensor Settings**: Better low-light performance

### Camera Configuration
```cpp
// With PSRAM (typical for Freenove boards)
config.frame_size = FRAMESIZE_UXGA;   // 1600x1200
config.jpeg_quality = 10;              // High quality
config.fb_count = 2;                   // Double buffering
config.fb_location = CAMERA_FB_IN_PSRAM;

// Sensor optimizations
s->set_gainceiling(s, GAINCEILING_4X);  // Better low-light
s->set_lenc(s, 1);                      // Lens correction
s->set_vflip/hmirror options available
```

## Uploading to ESP32-S3

### Arduino IDE Setup
1. **Install ESP32 Board Support**:
   - File → Preferences → Additional Board Manager URLs
   - Add: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Tools → Board → Boards Manager → Search "ESP32" → Install

2. **Board Selection**:
   - Board: "ESP32S3 Dev Module"
   - USB CDC On Boot: **"Disabled"** (use hardware serial)
   - PSRAM: **"Disabled"** (Freenove board may not have accessible PSRAM)
   - Flash Size: Match your board (4MB/8MB/16MB)
   - Upload Speed: 921600

3. **Partition Scheme**: 
   - "Huge APP (3MB No OTA/1MB SPIFFS)" for camera applications

### Using Arduino CLI
```powershell
# From obsybox root directory
.\bin\arduino-cli compile --fqbn esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=default,PSRAM=disabled,FlashSize=16M MonitorCam/ESP32S3_Freenove

.\bin\arduino-cli upload --fqbn esp32:esp32:esp32s3 --port COM3 MonitorCam/ESP32S3_Freenove
```

### Troubleshooting Upload
If upload fails:
1. **Hold BOOT button** while pressing RESET
2. Release RESET, keep BOOT pressed
3. Start upload
4. Release BOOT when "Connecting..." appears

Some boards enter bootloader automatically - try without BOOT button first.

## Web Interface

### Endpoints
- `/` - Main camera interface with controls
- `/capture` - Single JPEG snapshot
- `/stream` - Streaming endpoint (JavaScript-based refresh)
- `/led` - Toggle onboard LED (GPIO 48)
- `/health` - JSON system status

### Features
- **Fast Refresh**: Quick single-frame updates
- **Live Stream**: Auto-refreshing stream mode (500ms intervals)
- **LED Control**: Toggle board LED for illumination
- **System Health**: Monitor uptime, memory, WiFi signal
- **Responsive Design**: Mobile-friendly interface

### Access
Navigate to configured IP address:
```
http://192.168.1.149/
```

## System Monitoring

### Serial Debug Output (115200 baud)
- Boot diagnostics
- WiFi connection status
- PSRAM detection and size
- Camera initialization status
- Periodic health reports (every 30s)
- Request logging

### Health Monitoring Features
- Watchdog system (activates after 60s boot delay)
- Memory leak detection
- Camera failure tracking
- WiFi reconnection logic
- System responsiveness checks

### Status Reporting
Every 30 seconds via Serial:
```
=== System Status ===
Hardware: ESP32-S3 Freenove WROOM
Health: OK
WiFi: Connected
Signal: -45 dBm
IP: 192.168.1.149
Free Heap: 156432
Free PSRAM: 1843200
Uptime: 1234 seconds
Requests: 42
Last request: 15 seconds ago
==================
```

## Differences from AI Thinker ESP32-CAM

| Feature | AI Thinker (Original) | Freenove ESP32-S3 |
|---------|----------------------|-------------------|
| CPU | ESP32 Dual-core 240MHz | ESP32-S3 Dual-core 240MHz |
| RAM | 520KB SRAM | 512KB SRAM + 2-8MB PSRAM |
| Flash LED | GPIO 4 | GPIO 48 (RGB capable) |
| Max Resolution | SVGA (800x600) | UXGA (1600x1200) |
| USB | UART only | Native USB CDC |
| Camera Sensor | OV2640 | OV2640 (same) |

## Integration with ObsyBox

### MQTT Publishing
To add MQTT support (like other obsybox sensors), install PubSubClient:
```cpp
#include <PubSubClient.h>
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
mqtt.setServer("192.168.1.49", 1883);
```

### Typical ObsyBox Integration
1. Update static IP in code
2. Configure WiFi credentials
3. Upload to ESP32-S3
4. Add to monitoring dashboard
5. Integrate with weather safety system

## Performance Notes

### Expected Frame Rates
- **UXGA (1600x1200)**: ~5-8 fps
- **SXGA (1280x1024)**: ~8-12 fps  
- **XGA (1024x768)**: ~12-15 fps
- **SVGA (800x600)**: ~15-20 fps

### Memory Usage
With PSRAM, expect:
- Free Heap: ~150-200KB (SRAM)
- Free PSRAM: ~1.8-2MB (depends on frame buffer size)

### Power Consumption
- Active streaming: ~250-350mA @ 5V
- Idle with WiFi: ~80-120mA @ 5V
- Deep sleep: ~2.5mA @ 5V (not implemented)

## Future Enhancements

Potential additions for ESP32-S3 capabilities:
- [ ] MQTT telemetry publishing
- [ ] SD card image logging
- [ ] Time-lapse mode
- [ ] Motion detection
- [ ] AI-based cloud detection (TensorFlow Lite)
- [ ] Deep sleep power saving
- [ ] OTA firmware updates
- [ ] mDNS service discovery

## License
Part of the ObsyBox automated observatory project.
