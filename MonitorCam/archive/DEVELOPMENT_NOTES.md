# Development Notes Archive

## Hardware Issues Encountered

### CH340 Serial Driver Issue (Windows)
- **Problem**: Driver for CH340 serial chip was corrupted on Windows system
- **Solution**: Development moved to macOS for compilation and upload
- **Status**: Resolved by using macOS arduino-cli

### LED Pin Configuration
- **Problem**: Original examples used GPIO 22 for LED control
- **Fix**: Changed to GPIO 4 for AI Thinker ESP32-CAM flash LED
- **Location**: Updated in `app_httpd.cpp` and main sketch files
- **Status**: Resolved in current version

## Development History
- Started with Arduino CameraWebServer examples
- Multiple iterations for mobile compatibility
- Buffer overflow issues in mobile-optimized version
- Simplified to current stable ESP32_AP_Simple version

---
*This file preserved for reference - original CameraReadme content*