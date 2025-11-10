#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

// Access Point Configuration
const char *ap_ssid = "ESP32-CAM-AP";
const char *ap_password = "12345678";

IPAddress ap_local_IP(192, 168, 4, 1);
IPAddress ap_gateway(192, 168, 4, 1);
IPAddress ap_subnet(255, 255, 255, 0);

WebServer server(80);
bool cameraReady = false;
bool streamActive = false;
bool ledEnabled = false;
int currentResolution = FRAMESIZE_VGA;
int exposureTime = 0;  // 0 = auto, positive values for manual exposure

// Resolution options
const char* resolutionNames[] = {
  "96x96 (QQVGA)", "160x120 (QQVGA2)", "176x144 (QCIF)", "240x176 (HQVGA)",
  "240x240", "320x240 (QVGA)", "400x296 (CIF)", "480x320 (HVGA)",
  "640x480 (VGA)", "800x600 (SVGA)", "1024x768 (XGA)", "1280x1024 (SXGA)",
  "1600x1200 (UXGA)"
};

const framesize_t resolutionValues[] = {
  FRAMESIZE_96X96, FRAMESIZE_QQVGA2, FRAMESIZE_QCIF, FRAMESIZE_HQVGA,
  FRAMESIZE_240X240, FRAMESIZE_QVGA, FRAMESIZE_CIF, FRAMESIZE_HVGA,
  FRAMESIZE_VGA, FRAMESIZE_SVGA, FRAMESIZE_XGA, FRAMESIZE_SXGA,
  FRAMESIZE_UXGA
};

void setLED(bool state) {
#if defined(LED_GPIO_NUM)
  digitalWrite(LED_GPIO_NUM, state ? HIGH : LOW);
  ledEnabled = state;
#endif
}

void setResolution(framesize_t size) {
  if (cameraReady) {
    sensor_t *s = esp_camera_sensor_get();
    s->set_framesize(s, size);
    currentResolution = size;
    Serial.printf("Resolution changed to: %s\n", resolutionNames[size]);
  }
}

void setExposure(int value) {
  if (cameraReady) {
    sensor_t *s = esp_camera_sensor_get();
    if (value == 0) {
      // Auto exposure
      s->set_exposure_ctrl(s, 1);
      s->set_aec_value(s, 300);  // Default auto value
    } else {
      // Manual exposure
      s->set_exposure_ctrl(s, 0);
      s->set_aec_value(s, value);
    }
    exposureTime = value;
    Serial.printf("Exposure set to: %s\n", value == 0 ? "auto" : String(value).c_str());
  }
}

void handleRoot() {
  String html = "<!DOCTYPE html><html>";
  html += "<head><title>ESP32-CAM ObsyBox Advanced</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body{font-family:Arial,sans-serif;margin:20px;background:#f0f0f0;}";
  html += ".container{max-width:1000px;margin:0 auto;background:white;padding:20px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}";
  html += ".controls{background:#f8f9fa;padding:15px;border-radius:5px;margin:10px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;}";
  html += ".status{background:#e8f5e8;padding:10px;border-radius:5px;margin:10px 0;}";
  html += ".error{background:#ffe8e8;padding:10px;border-radius:5px;margin:10px 0;}";
  html += "button{background:#007bff;color:white;border:none;padding:10px 15px;border-radius:5px;cursor:pointer;margin:5px;}";
  html += "button:hover{background:#0056b3;}";
  html += "button.active{background:#28a745;}";
  html += "button.danger{background:#dc3545;}";
  html += "select,input{padding:8px;border:1px solid #ddd;border-radius:4px;margin:5px;}";
  html += ".image-container{text-align:center;margin:20px 0;}";
  html += ".control-group{margin:10px 0;}";
  html += "label{display:block;margin:5px 0;font-weight:bold;}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>🔭 ESP32-CAM ObsyBox Advanced Control</h1>";
  
  // Control Panel
  html += "<div class='controls'>";
  
  // Camera Mode Control
  html += "<div class='control-group'>";
  html += "<label>📷 Camera Mode:</label>";
  html += "<button id='stillBtn' onclick='setMode(\"still\")'>📸 Still Images</button>";
  html += "<button id='streamBtn' onclick='setMode(\"stream\")'>🎥 Live Stream</button>";
  html += "</div>";
  
  // Resolution Control
  html += "<div class='control-group'>";
  html += "<label>📐 Resolution:</label>";
  html += "<select id='resolution' onchange='changeResolution()'>";
  for (int i = 0; i < 13; i++) {
    html += "<option value='" + String(i) + "'";
    if (i == currentResolution) html += " selected";
    html += ">" + String(resolutionNames[i]) + "</option>";
  }
  html += "</select>";
  html += "</div>";
  
  // LED Control
  html += "<div class='control-group'>";
  html += "<label>💡 LED Flash:</label>";
  html += "<button id='ledBtn' onclick='toggleLED()' class='" + String(ledEnabled ? "active" : "") + "'>";
  html += ledEnabled ? "🔆 LED ON" : "💡 LED OFF";
  html += "</button>";
  html += "</div>";
  
  // Exposure Control
  html += "<div class='control-group'>";
  html += "<label>⏱️ Exposure:</label>";
  html += "<select id='exposure' onchange='changeExposure()'>";
  html += "<option value='0'" + String(exposureTime == 0 ? " selected" : "") + ">Auto</option>";
  html += "<option value='100'" + String(exposureTime == 100 ? " selected" : "") + ">Very Fast (100)</option>";
  html += "<option value='300'" + String(exposureTime == 300 ? " selected" : "") + ">Fast (300)</option>";
  html += "<option value='600'" + String(exposureTime == 600 ? " selected" : "") + ">Normal (600)</option>";
  html += "<option value='1200'" + String(exposureTime == 1200 ? " selected" : "") + ">Long (1200)</option>";
  html += "<option value='2000'" + String(exposureTime == 2000 ? " selected" : "") + ">Very Long (2000)</option>";
  html += "</select>";
  html += "</div>";
  
  html += "</div>";
  
  // Camera Status
  if (cameraReady) {
    html += "<div class='status'>";
    html += "<strong>📷 Camera Status:</strong> Ready<br>";
    html += "<strong>Mode:</strong> <span id='modeDisplay'>Still Images</span><br>";
    html += "<strong>Resolution:</strong> " + String(resolutionNames[currentResolution]) + "<br>";
    html += "<strong>LED:</strong> " + String(ledEnabled ? "Enabled" : "Disabled") + "<br>";
    html += "<strong>Exposure:</strong> " + String(exposureTime == 0 ? "Auto" : String(exposureTime));
    html += "</div>";
    
    // Image Display Area
    html += "<div class='image-container'>";
    html += "<div id='imageArea'>";
    html += "<img id='cameraImage' src='/capture' style='max-width:100%;border:2px solid #ddd;border-radius:8px;' alt='Camera Feed'>";
    html += "</div>";
    html += "<br>";
    html += "<button onclick='captureStill()'>📸 Capture New Image</button>";
    html += "<button onclick='downloadImage()'>💾 Download Image</button>";
    html += "</div>";
    
  } else {
    html += "<div class='error'>";
    html += "<strong>❌ Camera Status:</strong> Offline";
    html += "</div>";
  }
  
  // System Info
  html += "<div class='status'>";
  html += "<strong>🔧 System Info:</strong><br>";
  html += "Connected clients: " + String(WiFi.softAPgetStationNum()) + "<br>";
  html += "Free heap: " + String(ESP.getFreeHeap()/1024) + "KB<br>";
  html += "Uptime: " + String(millis()/60000) + " minutes";
  html += "</div>";
  
  // JavaScript for controls
  html += "<script>";
  html += "let currentMode = 'still';";
  html += "let streamInterval;";
  
  // Mode switching
  html += "function setMode(mode) {";
  html += "  currentMode = mode;";
  html += "  document.getElementById('modeDisplay').innerText = mode === 'still' ? 'Still Images' : 'Live Stream';";
  html += "  document.getElementById('stillBtn').className = mode === 'still' ? 'active' : '';";
  html += "  document.getElementById('streamBtn').className = mode === 'stream' ? 'active' : '';";
  html += "  if (mode === 'stream') { startStream(); } else { stopStream(); }";
  html += "}";
  
  // Streaming functions
  html += "function startStream() {";
  html += "  stopStream();";
  html += "  streamInterval = setInterval(() => {";
  html += "    document.getElementById('cameraImage').src = '/capture?t=' + Date.now();";
  html += "  }, 1000);";  // 1 FPS for streaming
  html += "}";
  
  html += "function stopStream() {";
  html += "  if (streamInterval) clearInterval(streamInterval);";
  html += "}";
  
  // Control functions
  html += "function captureStill() {";
  html += "  document.getElementById('cameraImage').src = '/capture?t=' + Date.now();";
  html += "}";
  
  html += "function downloadImage() {";
  html += "  window.open('/capture?download=1', '_blank');";
  html += "}";
  
  html += "function changeResolution() {";
  html += "  const res = document.getElementById('resolution').value;";
  html += "  fetch('/set_resolution?value=' + res).then(() => {";
  html += "    setTimeout(() => location.reload(), 1000);";  // Reload after resolution change
  html += "  });";
  html += "}";
  
  html += "function toggleLED() {";
  html += "  fetch('/toggle_led').then(response => response.text()).then(state => {";
  html += "    const btn = document.getElementById('ledBtn');";
  html += "    if (state === 'ON') {";
  html += "      btn.className = 'active';";
  html += "      btn.innerHTML = '🔆 LED ON';";
  html += "    } else {";
  html += "      btn.className = '';";
  html += "      btn.innerHTML = '💡 LED OFF';";
  html += "    }";
  html += "  });";
  html += "}";
  
  html += "function changeExposure() {";
  html += "  const exp = document.getElementById('exposure').value;";
  html += "  fetch('/set_exposure?value=' + exp).then(() => {";
  html += "    setTimeout(() => location.reload(), 500);";
  html += "  });";
  html += "}";
  
  html += "</script>";
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
  Serial.println("Served advanced control page");
}

void handleCapture() {
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera not available");
    return;
  }
  
  // Turn on LED if enabled
  if (ledEnabled) {
    setLED(true);
    delay(100);  // Give LED time to stabilize
  }
  
  camera_fb_t *fb = esp_camera_fb_get();
  
  // Turn off LED
  if (ledEnabled) {
    setLED(false);
  }
  
  if (!fb) {
    server.send(503, "text/plain", "Camera capture failed");
    Serial.println("Camera capture failed!");
    return;
  }
  
  // Check if download is requested
  if (server.hasArg("download")) {
    server.sendHeader("Content-Disposition", "attachment; filename=\"obsybox_" + String(millis()) + ".jpg\"");
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
  Serial.printf("Image captured and served (%d bytes)\n", fb->len);
}

void handleSetResolution() {
  if (server.hasArg("value")) {
    int resIndex = server.arg("value").toInt();
    if (resIndex >= 0 && resIndex < 13) {
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
#if defined(LED_GPIO_NUM)
  ledEnabled = !ledEnabled;
  setLED(false);  // Always off except during capture
  server.send(200, "text/plain", ledEnabled ? "ON" : "OFF");
  Serial.printf("LED flash %s\n", ledEnabled ? "enabled" : "disabled");
#else
  server.send(501, "text/plain", "LED not available");
#endif
}

void handleSetExposure() {
  if (server.hasArg("value")) {
    int expValue = server.arg("value").toInt();
    setExposure(expValue);
    server.send(200, "text/plain", "Exposure set to " + String(expValue == 0 ? "auto" : String(expValue)));
  } else {
    server.send(400, "text/plain", "Missing exposure value");
  }
}

void handleCapture() {
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera not available");
    return;
  }
  
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(503, "text/plain", "Camera capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
  Serial.println("Image served");
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
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;  // Start with VGA
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  
  if (psramFound()) {
    Serial.println("PSRAM found - using for frame buffer");
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("PSRAM not found - using DRAM");
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.frame_size = FRAMESIZE_VGA;
  }
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }
  
  // Configure camera sensor
  sensor_t *s = esp_camera_sensor_get();
  
  // Flip settings for AI Thinker model
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  
  // Set default frame size
  s->set_framesize(s, FRAMESIZE_VGA);
  currentResolution = FRAMESIZE_VGA;
  
  // Configure exposure for better low-light performance
  s->set_exposure_ctrl(s, 1);      // Enable auto exposure
  s->set_aec_value(s, 300);        // Default exposure value
  s->set_gain_ctrl(s, 1);          // Enable auto gain
  s->set_agc_gain(s, 0);           // Auto gain value
  s->set_gainceiling(s, (gainceiling_t)6);  // Gain ceiling
  
  // White balance and color settings
  s->set_whitebal(s, 1);           // Enable auto white balance
  s->set_awb_gain(s, 1);           // Auto white balance gain
  s->set_wb_mode(s, 0);            // Auto white balance mode
  
  // Quality settings for observatory use
  s->set_contrast(s, 0);           // Normal contrast
  s->set_brightness(s, 0);         // Normal brightness
  s->set_saturation(s, 0);         // Normal saturation
  s->set_sharpness(s, 0);          // Normal sharpness
  s->set_denoise(s, 1);            // Enable denoise for night shots
  
  // Setup LED if available
#if defined(LED_GPIO_NUM)
  pinMode(LED_GPIO_NUM, OUTPUT);
  digitalWrite(LED_GPIO_NUM, LOW);  // LED off by default
  Serial.printf("LED flash configured on pin %d\n", LED_GPIO_NUM);
#else
  Serial.println("LED flash not available on this board");
#endif
  
  Serial.println("Camera initialized successfully!");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== ESP32-CAM ObsyBox Advanced Control ===");
  
  // Start Access Point first
  Serial.println("Starting Access Point...");
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet);
  
  if (WiFi.softAP(ap_ssid, ap_password)) {
    Serial.println("Access Point started successfully!");
    Serial.print("SSID: ");
    Serial.println(ap_ssid);
    Serial.print("IP: ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("AP failed to start!");
    return;
  }
  
  // Initialize camera
  cameraReady = initCamera();
  if (cameraReady) {
    Serial.println("Camera ready with advanced controls!");
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
  
  Serial.println("Advanced web server started!");
  Serial.println("🔭 FEATURES AVAILABLE:");
  Serial.println("  • Still capture & live streaming");
  Serial.println("  • Resolution control (96x96 to UXGA)");
  Serial.println("  • LED flash control");
  Serial.println("  • Manual exposure settings");
  Serial.println("  • Image download capability");
  Serial.println("Connect to '" + String(ap_ssid) + "' and go to http://192.168.4.1");
  Serial.println("===========================");
}

void loop() {
  server.handleClient();
  
  static unsigned long lastStatus = 0;
  if (millis() - lastStatus > 30000) {
    lastStatus = millis();
    Serial.printf("Status: %d clients, %d heap, camera: %s\n", 
                  WiFi.softAPgetStationNum(), 
                  ESP.getFreeHeap(),
                  cameraReady ? "OK" : "FAIL");
  }
  
  delay(100);
}