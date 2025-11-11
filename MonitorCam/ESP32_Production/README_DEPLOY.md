# ESP32-CAM Deployment Version

## 🚀 **Network Station Mode**

This version connects to your local WiFi network instead of creating its own Access Point. Perfect for observatory deployment where the camera needs to be accessible from the existing network.

## 📋 **Pre-Deployment Setup**

### 1. Configure WiFi Credentials
Edit `arduino_secrets.h` with your network details:
```cpp
#define SECRET_SSID "YourNetworkName"
#define SECRET_PASS "YourNetworkPassword"
```

### 2. Upload Process
```bash
cd /path/to/obsybox
arduino-cli compile --fqbn esp32:esp32:esp32cam MonitorCam/ESP32_Deploy
arduino-cli upload --fqbn esp32:esp32:esp32cam --port /dev/cu.usbserial-XXXX MonitorCam/ESP32_Deploy
```

## 🌐 **Deployment Features**

### **WiFi Connection**
- **Connects** to existing network using `arduino_secrets.h`
- **Auto-reconnect** if connection is lost
- **30-second timeout** during initial connection
- **Signal monitoring** with RSSI reporting

### **Network Information Display**
- **Network SSID** shown in web interface
- **Local IP Address** for direct access
- **Signal Strength** monitoring
- **Connection Status** in health reports

### **Enhanced Monitoring**
- **WiFi status** included in system health
- **Network diagnostics** in serial output
- **Connection recovery** automatic retry
- **Signal strength** logging

## 📊 **Post-Deployment Access**

### **Finding the Device**
1. **Check router's DHCP table** for new device with MAC: `c8:f0:9e:4d:e8:30`
2. **Serial monitor** will show assigned IP address
3. **Network scanner** apps can locate the device

### **Web Interface**
- **URL**: `http://[assigned-ip-address]`
- **Example**: `http://192.168.1.XXX`
- **Same interface** as AP mode but shows network details

## 🔧 **Observatory Integration**

### **Static IP Configuration (Recommended)**
Configure router to assign static IP for reliable access:
1. Note the device MAC address: `c8:f0:9e:4d:e8:30`
2. Set static DHCP reservation in router
3. Use consistent IP for ObsyBox automation scripts

### **Port Forwarding (Optional)**
For remote access outside the local network:
1. Forward port 80 to camera's internal IP
2. Access via external IP or DDNS
3. **Security**: Consider VPN instead of direct exposure

### **Network Requirements**
- **2.4GHz WiFi** (ESP32 doesn't support 5GHz)
- **WPA/WPA2** security (WEP not recommended)
- **DHCP enabled** or manual static IP configuration
- **Firewall** may need exception for port 80

## 🛠 **Troubleshooting**

### **Connection Issues**
- **Serial Monitor**: Check for WiFi error messages
- **Credentials**: Verify SSID/password in `arduino_secrets.h`
- **Network**: Ensure 2.4GHz band is enabled
- **Distance**: Check signal strength (should be > -70 dBm)

### **Can't Access Web Interface**
- **IP Address**: Check serial monitor for assigned IP
- **Firewall**: Temporarily disable to test
- **Browser**: Try different device/browser
- **Network**: Ensure same subnet as camera

### **Performance Issues**
- **Signal Strength**: Move closer to router or add WiFi extender
- **Network Load**: Reduce other network traffic
- **Router**: Restart router if connection is unstable
- **Channel**: Change WiFi channel if crowded

## 📈 **Observatory Monitoring**

### **Integration Points**
- **HTTP API**: All endpoints work same as AP mode
- **Health Endpoint**: `http://[ip]/health` for status monitoring
- **MQTT Integration**: Add MQTT client for ObsyBox system integration
- **Automation**: Schedule captures via HTTP requests

### **Recommended Monitoring Script**
```python
import requests
import json

def check_camera_status(ip_address):
    try:
        response = requests.get(f"http://{ip_address}/health", timeout=5)
        data = response.json()
        print(f"Camera Status: {data['status']}")
        print(f"Signal: {data['wifiRSSI']} dBm")
        print(f"Free Memory: {data['freeHeap']} bytes")
        return True
    except:
        print("Camera unreachable")
        return False
```

---

**Ready for ObsyBox observatory deployment! 🔭**