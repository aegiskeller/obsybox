#include "esp_camera.h"
#include "camera_pins.h"
#include <WiFi.h>
#include <WebServer.h>

// Access Point Configuration
const char* ap_ssid = "ESP32-CAM-AP";
const char* ap_password = "12345678";
IPAddress ap_local_IP(192, 168, 4, 1);
IPAddress ap_gateway(192, 168, 4, 1);
IPAddress ap_subnet(255, 255, 255, 0);

WebServer server(80);

// Camera and LED control
bool cameraReady = false;
bool streamActive = false;
bool ledEnabled = false;
int currentResolution = FRAMESIZE_VGA;
int exposureTime = 0;  // 0 = auto, positive values for manual exposure

// LED Pin configurations for AI Thinker boards
#define FLASH_LED_PIN 4    // Main flash LED
#define BUILTIN_LED_PIN 33 // Secondary LED (if available)

// Resolution options
const char* resolutionNames[] = {
  "96x96", "QQVGA (160x120)", "QCIF (176x144)", "HQVGA (240x176)",
  "240x240", "QVGA (320x240)", "CIF (400x296)", "HVGA (480x320)",
  "VGA (640x480)", "SVGA (800x600)", "XGA (1024x768)", "HD (1280x720)",
  "SXGA (1280x1024)", "UXGA (1600x1200)"
};

framesize_t resolutionValues[] = {
  FRAMESIZE_96X96, FRAMESIZE_QQVGA, FRAMESIZE_QCIF, FRAMESIZE_HQVGA,
  FRAMESIZE_240X240, FRAMESIZE_QVGA, FRAMESIZE_CIF, FRAMESIZE_HVGA,
  FRAMESIZE_VGA, FRAMESIZE_SVGA, FRAMESIZE_XGA, FRAMESIZE_HD,
  FRAMESIZE_SXGA, FRAMESIZE_UXGA
};

void setLED(bool state) {
  // Try both LED pins for maximum compatibility
  digitalWrite(FLASH_LED_PIN, state ? HIGH : LOW);
  digitalWrite(BUILTIN_LED_PIN, state ? HIGH : LOW);
  ledEnabled = state;
  
  Serial.printf("LED %s (Flash: %d, Builtin: %d)\n", 
                state ? "ON" : "OFF", 
                digitalRead(FLASH_LED_PIN), 
                digitalRead(BUILTIN_LED_PIN));
}

void setResolution(framesize_t size) {
  if (cameraReady) {
    sensor_t *s = esp_camera_sensor_get();
    if (s->set_framesize(s, size) == 0) {
      currentResolution = size;
      Serial.printf("Resolution changed to: %s\n", resolutionNames[size]);
    }
  }
}

void handleRoot() {
  String html = R"(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM ObsyBox Control</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            padding: 20px; 
            background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
            color: #ffffff; 
            line-height: 1.6;
            min-height: 100vh;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: linear-gradient(145deg, #111111, #1e1e1e);
            border: 3px solid #00ff41;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 
                0 0 50px rgba(0, 255, 65, 0.3),
                inset 0 0 50px rgba(0, 255, 65, 0.05);
        }
        .header { 
            text-align: center; 
            margin-bottom: 40px; 
            border-bottom: 3px solid #00ff41;
            padding-bottom: 25px;
            position: relative;
        }
        .header::after {
            content: '';
            position: absolute;
            bottom: -3px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 3px;
            background: linear-gradient(90deg, transparent, #00ff41, transparent);
        }
        .header h1 { 
            font-size: 3em; 
            color: #00ff41; 
            text-shadow: 
                0 0 10px #00ff41,
                0 0 20px #00ff41,
                0 0 30px #00ff41;
            font-weight: 800;
            letter-spacing: 2px;
            animation: glow 2s ease-in-out infinite alternate;
        }
        @keyframes glow {
            from { text-shadow: 0 0 10px #00ff41, 0 0 20px #00ff41, 0 0 30px #00ff41; }
            to { text-shadow: 0 0 20px #00ff41, 0 0 30px #00ff41, 0 0 40px #00ff41; }
        }
        .header p { 
            margin: 15px 0 0 0; 
            color: #cccccc; 
            font-size: 1.3em;
            font-weight: 300;
            letter-spacing: 1px;
        }
        .controls { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 25px; 
            margin-bottom: 35px; 
        }
        .control-group { 
            background: linear-gradient(145deg, #1a1a1a, #2a2a2a);
            border: 2px solid #333333;
            padding: 25px; 
            border-radius: 15px; 
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }
        .control-group::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 255, 65, 0.1), transparent);
            transition: left 0.5s ease;
        }
        .control-group:hover::before {
            left: 100%;
        }
        .control-group:hover {
            border-color: #00ff41;
            transform: translateY(-5px);
            box-shadow: 
                0 10px 30px rgba(0, 0, 0, 0.5),
                0 0 30px rgba(0, 255, 65, 0.3);
        }
        .control-group h3 { 
            margin-bottom: 20px; 
            color: #00ff41; 
            font-size: 1.5em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
        }
        button { 
            background: linear-gradient(145deg, #00aa33, #00ff41); 
            color: #000000; 
            border: none; 
            padding: 15px 25px; 
            border-radius: 10px; 
            cursor: pointer; 
            margin: 8px; 
            font-size: 14px; 
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s ease;
            box-shadow: 
                0 5px 15px rgba(0, 255, 65, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
            position: relative;
            overflow: hidden;
        }
        button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s ease;
        }
        button:hover::before {
            left: 100%;
        }
        button:hover { 
            background: linear-gradient(145deg, #00ff41, #33ff66); 
            transform: translateY(-3px);
            box-shadow: 
                0 8px 25px rgba(0, 255, 65, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        button:active {
            transform: translateY(-1px);
            box-shadow: 
                0 3px 15px rgba(0, 255, 65, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }
        button.danger { 
            background: linear-gradient(145deg, #cc0000, #ff0000); 
            color: #ffffff;
            box-shadow: 
                0 5px 15px rgba(255, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }
        button.danger:hover { 
            background: linear-gradient(145deg, #ff0000, #ff3333); 
            box-shadow: 
                0 8px 25px rgba(255, 0, 0, 0.4),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
        }
        select { 
            padding: 12px; 
            border-radius: 10px; 
            border: 2px solid #333333; 
            background: linear-gradient(145deg, #222222, #333333); 
            color: #ffffff; 
            margin: 8px; 
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            width: 100%;
            cursor: pointer;
        }
        select:focus {
            outline: none;
            border-color: #00ff41;
            box-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
        }
        input[type="range"] {
            width: 100%;
            height: 8px;
            background: linear-gradient(90deg, #333333, #555555);
            border: none;
            border-radius: 4px;
            margin: 15px 0;
            cursor: pointer;
            outline: none;
        }
        input[type="range"]::-webkit-slider-thumb {
            appearance: none;
            width: 25px;
            height: 25px;
            background: linear-gradient(145deg, #00ff41, #33ff66);
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 
                0 0 15px rgba(0, 255, 65, 0.7),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
        }
        input[type="range"]::-webkit-slider-thumb:hover {
            transform: scale(1.2);
            box-shadow: 
                0 0 25px rgba(0, 255, 65, 0.9),
                inset 0 1px 0 rgba(255, 255, 255, 0.5);
        }
        .image-container { 
            text-align: center; 
            margin: 35px 0; 
            background: linear-gradient(145deg, #1a1a1a, #2a2a2a);
            border: 3px solid #333333;
            border-radius: 15px;
            padding: 25px;
            transition: all 0.3s ease;
        }
        .image-container:hover {
            border-color: #00ff41;
            box-shadow: 0 0 30px rgba(0, 255, 65, 0.3);
        }
        .image-container img { 
            max-width: 100%; 
            border-radius: 12px; 
            box-shadow: 
                0 10px 40px rgba(0, 0, 0, 0.8),
                0 0 20px rgba(0, 255, 65, 0.2);
            border: 2px solid #444444;
            transition: all 0.4s ease;
        }
        .image-container img:hover {
            transform: scale(1.05);
            border-color: #00ff41;
            box-shadow: 
                0 15px 60px rgba(0, 0, 0, 0.9),
                0 0 40px rgba(0, 255, 65, 0.4);
        }
        .status { 
            padding: 25px; 
            background: linear-gradient(145deg, #1a1a1a, #2a2a2a);
            border: 2px solid #333333;
            border-radius: 15px; 
            margin: 25px 0; 
            font-family: 'Courier New', monospace;
            position: relative;
        }
        .status::before {
            content: 'SYSTEM STATUS';
            position: absolute;
            top: -12px;
            left: 20px;
            background: linear-gradient(145deg, #1a1a1a, #2a2a2a);
            color: #00ff41;
            padding: 0 10px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1px;
        }
        .status-item {
            margin: 12px 0;
            font-size: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-label {
            color: #00ff41;
            font-weight: 700;
            text-shadow: 0 0 5px rgba(0, 255, 65, 0.5);
        }
        .status-value {
            color: #ffffff;
            font-weight: 500;
        }
        .led-indicator { 
            display: inline-block; 
            width: 20px; 
            height: 20px; 
            border-radius: 50%; 
            margin-right: 12px; 
            background: #333333;
            border: 2px solid #555555;
            transition: all 0.3s ease;
            position: relative;
        }
        .led-indicator.on { 
            background: radial-gradient(circle, #ff0000, #cc0000); 
            border-color: #ff0000;
            box-shadow: 
                0 0 20px rgba(255, 0, 0, 0.8),
                inset 0 1px 0 rgba(255, 255, 255, 0.3);
            animation: ledPulse 1.5s infinite;
        }
        @keyframes ledPulse {
            0%, 100% { 
                box-shadow: 
                    0 0 20px rgba(255, 0, 0, 0.8),
                    inset 0 1px 0 rgba(255, 255, 255, 0.3);
            }
            50% { 
                box-shadow: 
                    0 0 40px rgba(255, 0, 0, 1),
                    inset 0 1px 0 rgba(255, 255, 255, 0.5);
            }
        }
        .control-value {
            background: linear-gradient(145deg, #222222, #333333);
            border: 1px solid #444444;
            padding: 12px 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-family: 'Courier New', monospace;
            color: #00ff41;
            font-weight: 600;
            text-align: center;
            box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.3);
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        @media (max-width: 768px) {
            .container { padding: 20px; }
            .controls { grid-template-columns: 1fr; }
            .grid-2 { grid-template-columns: 1fr; }
            .header h1 { font-size: 2.5em; }
            button { padding: 12px 20px; }
        }
        .terminal-text {
            font-family: 'Courier New', monospace;
            color: #00ff41;
            text-shadow: 0 0 5px rgba(0, 255, 65, 0.5);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ESP32-CAM OBSYBOX</h1>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <h3>CAPTURE MODE</h3>
                <div class="grid-2">
                    <button onclick="toggleStream()">TOGGLE STREAM</button>
                    <button onclick="captureImage()">CAPTURE STILL</button>
                </div>
                <div class="control-value" id="streamStatus">STREAM: OFFLINE</div>
            </div>
            
            <div class="control-group">
                <h3>📐 RESOLUTION</h3>
                <select id="resolution" onchange="setResolution()">)";

  // Add resolution options
  for (int i = 0; i < 14; i++) {
    html += "<option value='" + String(i) + "'";
    if (i == currentResolution) html += " selected";
    html += ">" + String(resolutionNames[i]) + "</option>";
  }
  
  html += R"(
                </select>
                <div class="control-value">CURRENT: )" + String(resolutionNames[currentResolution]) + R"(</div>
            </div>
            
            <div class="control-group">
                <h3>LED FLASH</h3>
                <span class="led-indicator)" + String(ledEnabled ? " on" : "") + R"("></span>
                <button onclick="toggleLED()">)" + String(ledEnabled ? "DISABLE LED" : "ENABLE LED") + R"(</button>
                <div class="control-value">STATUS: )" + String(ledEnabled ? "ACTIVE" : "INACTIVE") + R"(</div>
            </div>
            
            <div class="control-group">
                <h3>EXPOSURE</h3>
                <div class="grid-2">
                    <button onclick="setAutoExposure()">AUTO MODE</button>
                    <button onclick="setManualExposure()">MANUAL MODE</button>
                </div>
                <input type="range" id="exposure" min="0" max="1000" value=")" + String(exposureTime) + R"(" onchange="setExposure()">
                <div class="control-value">VALUE: )" + String(exposureTime == 0 ? "AUTO" : String(exposureTime)) + R"(</div>
            </div>
        </div>
        
        <div class="status">
            <div class="status-item">
                <span class="status-label">CAMERA MODULE:</span>
                <span class="status-value">)" + String(cameraReady ? "ONLINE" : "OFFLINE") + R"(</span>
            </div>
            <div class="status-item">
                <span class="status-label">RESOLUTION:</span>
                <span class="status-value">)" + String(resolutionNames[currentResolution]) + R"(</span>
            </div>
            <div class="status-item">
                <span class="status-label">LED FLASH:</span>
                <span class="status-value">)" + String(ledEnabled ? "ENABLED" : "DISABLED") + R"(</span>
            </div>
            <div class="status-item">
                <span class="status-label">ACCESS POINT:</span>
                <span class="status-value">)" + String(ap_ssid) + R"(</span>
            </div>
            <div class="status-item">
                <span class="status-label">IP ADDRESS:</span>
                <span class="status-value">192.168.4.1</span>
            </div>
        </div>
        
        <div class="image-container">
            <img id="cameraImage" src="/capture" alt="Camera feed loading..." onclick="refreshImage()">
            <br><br>
            <div class="grid-2">
                <button onclick="refreshImage()">REFRESH IMAGE</button>
                <button onclick="downloadImage()">DOWNLOAD IMAGE</button>
            </div>
        </div>
    </div>

    <script>
        let streamActive = false;
        let refreshInterval;
        
        function toggleStream() {
            streamActive = !streamActive;
            const statusEl = document.getElementById('streamStatus');
            
            if (streamActive) {
                statusEl.textContent = 'STREAM: ONLINE';
                statusEl.style.color = '#00ff41';
                startImageRefresh();
            } else {
                statusEl.textContent = 'STREAM: OFFLINE';
                statusEl.style.color = '#ff0000';
                stopImageRefresh();
            }
        }
        
        function startImageRefresh() {
            refreshInterval = setInterval(refreshImage, 800); // Faster refresh for streaming
        }
        
        function stopImageRefresh() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        }
        
        function captureImage() {
            refreshImage();
        }
        
        function refreshImage() {
            const img = document.getElementById('cameraImage');
            img.src = '/capture?' + new Date().getTime();
        }
        
        function setResolution() {
            const select = document.getElementById('resolution');
            fetch('/set_resolution?value=' + select.value)
                .then(response => response.text())
                .then(data => {
                    console.log(data);
                    setTimeout(refreshImage, 500);
                });
        }
        
        function toggleLED() {
            fetch('/toggle_led')
                .then(response => response.text())
                .then(data => {
                    console.log(data);
                    setTimeout(() => location.reload(), 500);
                });
        }
        
        function setAutoExposure() {
            fetch('/set_exposure?value=0')
                .then(response => response.text())
                .then(data => {
                    console.log(data);
                    document.getElementById('exposure').value = 0;
                });
        }
        
        function setManualExposure() {
            const slider = document.getElementById('exposure');
            if (slider.value == 0) slider.value = 300;
            setExposure();
        }
        
        function setExposure() {
            const slider = document.getElementById('exposure');
            fetch('/set_exposure?value=' + slider.value)
                .then(response => response.text())
                .then(data => console.log(data));
        }
        
        function downloadImage() {
            const link = document.createElement('a');
            link.href = '/capture?' + new Date().getTime();
            link.download = 'obsybox_capture_' + new Date().toISOString().slice(0,19).replace(/:/g, '-') + '.jpg';
            link.click();
        }
        
        // Auto-refresh image every 3 seconds if not streaming
        setInterval(() => {
            if (!streamActive) {
                refreshImage();
            }
        }, 3000);
        
        // Initial image load
        setTimeout(refreshImage, 1000);
    </script>
</body>
</html>
)";

  server.send(200, "text/html", html);
}

void handleCapture() {
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera not available");
    return;
  }
  
  // Flash LED briefly during capture if enabled
  if (ledEnabled) {
    setLED(true);
    delay(50);  // Very brief flash
  }
  
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    if (ledEnabled) setLED(false);
    server.send(503, "text/plain", "Camera capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
  
  // Turn off LED after capture
  if (ledEnabled) {
    delay(25);
    setLED(false);
  }
  
  Serial.println("Image captured and served");
}

void handleSetResolution() {
  if (server.hasArg("value")) {
    int resIndex = server.arg("value").toInt();
    if (resIndex >= 0 && resIndex < 14) {
      setResolution(resolutionValues[resIndex]);
      server.send(200, "text/plain", "Resolution set to " + String(resolutionNames[resIndex]));
    } else {
      server.send(400, "text/plain", "Invalid resolution index");
    }
  } else {
    server.send(400, "text/plain", "Missing resolution value");
  }
}

void handleToggleLED() {
  ledEnabled = !ledEnabled;
  setLED(ledEnabled);
  server.send(200, "text/plain", "LED " + String(ledEnabled ? "enabled" : "disabled"));
}

void handleSetExposure() {
  if (server.hasArg("value")) {
    exposureTime = server.arg("value").toInt();
    
    if (cameraReady) {
      sensor_t *s = esp_camera_sensor_get();
      if (exposureTime == 0) {
        s->set_exposure_ctrl(s, 1);  // Enable auto exposure
        Serial.println("Auto exposure enabled");
      } else {
        s->set_exposure_ctrl(s, 0);  // Disable auto exposure
        s->set_aec_value(s, exposureTime);
        Serial.printf("Manual exposure set to: %d\n", exposureTime);
      }
    }
    
    server.send(200, "text/plain", "Exposure set to " + String(exposureTime == 0 ? "auto" : String(exposureTime)));
  } else {
    server.send(400, "text/plain", "Missing exposure value");
  }
}

bool initCamera() {
  Serial.println("Initializing camera...");
  
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  if (psramFound()) {
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 10;
    config.fb_count = 2;
    Serial.println("PSRAM found - using for camera buffer");
  } else {
    config.fb_location = CAMERA_FB_IN_DRAM;
    Serial.println("No PSRAM - using DRAM for camera buffer");
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return false;
  }

  Serial.println("Camera initialized successfully!");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== ESP32-CAM ObsyBox Dark Theme ===");
  
  // Initialize LED pins with proper configuration
  pinMode(FLASH_LED_PIN, OUTPUT);
  pinMode(BUILTIN_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);
  digitalWrite(BUILTIN_LED_PIN, LOW);
  Serial.printf("LED pins configured: Flash=%d, Builtin=%d\n", FLASH_LED_PIN, BUILTIN_LED_PIN);
  
  // LED startup test
  Serial.println("Testing LED system...");
  for (int i = 0; i < 3; i++) {
    setLED(true);
    delay(200);
    setLED(false);
    delay(200);
  }
  Serial.println("LED test complete");
  
  // Start Access Point
  Serial.println("Starting Access Point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet);
  
  if (WiFi.softAP(ap_ssid, ap_password)) {
    Serial.println("Access Point started successfully!");
    Serial.printf("   SSID: %s\n", ap_ssid);
    Serial.printf("   IP: %s\n", WiFi.softAPIP().toString().c_str());
  } else {
    Serial.println("AP failed to start!");
    return;
  }
  
  // Initialize camera
  cameraReady = initCamera();
  if (cameraReady) {
    Serial.println("Camera ready with dark theme interface!");
  } else {
    Serial.println("Camera failed - continuing with AP only");
  }
  
  // Setup web server routes
  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  server.on("/set_resolution", handleSetResolution);
  server.on("/toggle_led", handleToggleLED);
  server.on("/set_exposure", handleSetExposure);
  
  server.begin();
  
  Serial.println("DARK THEME WEB SERVER STARTED!");
  Serial.printf("Connect to: %s\n", ap_ssid);
  Serial.println("Navigate to: http://192.168.4.1");
  Serial.println("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

void loop() {
  server.handleClient();
  delay(10);
}