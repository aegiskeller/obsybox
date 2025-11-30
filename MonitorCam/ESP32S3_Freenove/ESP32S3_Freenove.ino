#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "arduino_secrets.h"

// ===================
// Select camera model - Freenove ESP32-S3 WROOM
// ===================
#define CAMERA_MODEL_FREENOVE_ESP32S3_WROOM
#include "camera_pins.h"

// Watchdog and health monitoring
#define WDT_TIMEOUT 30000  // 30 seconds in milliseconds
unsigned long lastActivity = 0;
unsigned long bootTime = 0;

// LED control - GPIO 48 for camera flash LED (PWM controlled)
#define LED_PIN 4
#define LED_CHANNEL 15  // Use LEDC channel 15 (channel 0 is used by camera)
bool ledState = false;

// Health monitoring
unsigned long requestCount = 0;
unsigned long lastRequestTime = 0;
unsigned long lastCameraError = 0;
bool systemHealthy = true;

WebServer server(80);
bool cameraReady = false;

void handleRoot() {
  String html = "<!DOCTYPE html><html>";
  html += "<head><title>ObsyBox Monitor Camera (ESP32-S3)</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body{font-family:'Courier New',monospace;margin:0;background:#000000;color:#00ff00;}";
  html += ".container{max-width:800px;margin:20px auto;background:#111111;padding:20px;border:2px solid #00ff00;border-radius:10px;}";
  html += ".status{background:#001100;color:#00ff00;padding:15px;border:1px solid #00ff00;border-radius:5px;margin:15px 0;text-shadow:0 0 5px #004400;}";
  html += "h1{color:#ffffff;text-shadow:0 0 10px #00ff00;border-bottom:2px solid #00ff00;padding-bottom:10px;}";
  html += "img{max-width:100%;height:auto;border:3px solid #00ff00;box-shadow:0 0 15px #004400;background:#222222;}";
  html += "button{background:#001100;color:#00ff00;border:2px solid #00ff00;padding:12px 24px;border-radius:5px;cursor:pointer;margin:8px;font-family:'Courier New',monospace;font-size:16px;transition:all 0.3s;}";
  html += "button:hover{background:#00ff00;color:#000000;box-shadow:0 0 10px #00ff00;}";
  html += "#stream-status{color:#ffff00;font-weight:bold;margin:15px 0;text-shadow:0 0 5px #444400;}";
  html += "#led-status{color:#ff8800;font-weight:bold;margin:15px 0;text-shadow:0 0 5px #442200;}";
  html += "#health-status{color:#88ff88;font-weight:bold;margin:15px 0;text-shadow:0 0 5px #224422;}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>ObsyBox Monitor Camera #2</h1>";
  html += "<div class='status'>Hardware: ESP32-S3 Freenove WROOM</div>";
  
  if (cameraReady) {
    html += "<div class='status'>Camera Status: Ready</div>";
    html += "<img src='/capture' id='camera' alt='Camera Feed'>";
    html += "<br><button onclick=\"document.getElementById('camera').src='/capture?'+Date.now()\">Refresh</button>";
    html += "<button onclick=\"fastRefresh()\">Fast Refresh</button>";
    html += "<button onclick=\"startStream()\">Start Stream</button>";
    html += "<button onclick=\"stopStream()\">Stop Stream</button>";
    html += "<button onclick=\"toggleLED()\">Toggle LED</button>";
    html += "<br><br>";
    html += "<p id='stream-status'>Click 'Start Stream' for live video</p>";
    html += "<p id='led-status'>LED Status: OFF</p>";
    html += "<button onclick=\"checkHealth()\">System Health</button>";
    html += "<p id='health-status'>Click 'System Health' to check status</p>";
  } else {
    html += "<div class='error'>Camera Status: Not Ready</div>";
  }
  
  html += "<div class='status'>";
  html += "Network: " + WiFi.SSID() + "<br>";
  html += "IP: " + WiFi.localIP().toString() + "<br>";
  html += "Signal: " + String(WiFi.RSSI()) + " dBm<br>";
  html += "Free Heap: " + String(ESP.getFreeHeap()) + " bytes<br>";
  html += "PSRAM Free: " + String(ESP.getFreePsram()) + " bytes<br>";
  html += "Uptime: " + String(millis()/1000) + " seconds";
  html += "</div>";
  
  html += "</div>";
  
  html += "<script>";
  html += "let streaming = false;";
  html += "let streamTimer = null;";
  html += "let ledOn = false;";
  html += "function startStream() {";
  html += "  if (!streaming) {";
  html += "    streaming = true;";
  html += "    document.getElementById('stream-status').textContent = 'Live streaming active';";
  html += "    refreshStream();";
  html += "    streamTimer = setInterval(refreshStream, 500);"; // 500ms refresh for faster updates
  html += "  }";
  html += "}";
  html += "function refreshStream() {";
  html += "  document.getElementById('camera').src = '/stream?' + Date.now();";
  html += "}";
  html += "function stopStream() {";
  html += "  if (streaming) {";
  html += "    streaming = false;";
  html += "    if (streamTimer) {";
  html += "      clearInterval(streamTimer);";
  html += "      streamTimer = null;";
  html += "    }";
  html += "    document.getElementById('camera').src = '/capture?' + Date.now();";
  html += "    document.getElementById('stream-status').textContent = 'Stream stopped - back to capture mode';";
  html += "  }";
  html += "}";
  html += "function toggleLED() {";
  html += "  fetch('/led').then(response => response.text()).then(data => {";
  html += "    ledOn = !ledOn;";
  html += "    document.getElementById('led-status').textContent = 'LED Status: ' + (ledOn ? 'ON' : 'OFF');";
  html += "  });";
  html += "}";
  html += "function checkHealth() {";
  html += "  fetch('/health').then(response => response.json()).then(data => {";
  html += "    const uptime = Math.floor(data.uptime / 1000);";
  html += "    const status = data.status === 'healthy' ? '✓ HEALTHY' : '⚠ DEGRADED';";
  html += "    document.getElementById('health-status').textContent = ";
  html += "      status + ' | Uptime: ' + uptime + 's | Requests: ' + data.requestCount + ' | Free RAM: ' + data.freeHeap;";
  html += "  }).catch(err => {";
  html += "    document.getElementById('health-status').textContent = '❌ SYSTEM ERROR - Check connection';";
  html += "  });";
  html += "}";
  html += "function fastRefresh() {";
  html += "  const img = document.getElementById('camera');";
  html += "  img.style.opacity = '0.7';";
  html += "  img.src = '/capture?fast&t=' + Date.now();";
  html += "  img.onload = () => { img.style.opacity = '1'; };";
  html += "}";
  html += "</script>";
  
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleCapture() {
  requestCount++;
  lastRequestTime = millis();
  checkSystemHealth();
  
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera not ready");
    return;
  }
  
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    lastCameraError = millis();
    Serial.println("Camera capture failed");
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.sendHeader("Pragma", "no-cache");
  server.sendHeader("Expires", "0");
  server.sendHeader("Connection", "close");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
}

void handleStream() {
  requestCount++;
  lastRequestTime = millis();
  checkSystemHealth();
  
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera not ready");
    return;
  }
  
  // Instead of MJPEG stream, just return a single capture
  // JavaScript will handle the refresh for streaming
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    lastCameraError = millis();
    Serial.println("Stream capture failed");
    server.send(503, "text/plain", "Camera capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.sendHeader("Pragma", "no-cache");
  server.sendHeader("Expires", "0");
  server.send_P(200, "image/jpeg", (const char*)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
}

void checkSystemHealth() {
  unsigned long currentTime = millis();
  
  // Update activity timestamp (only for web requests)
  lastActivity = currentTime;
  
  // Check if camera has been failing frequently
  if (lastCameraError > 0 && (currentTime - lastCameraError) < 10000) {
    Serial.println("Camera errors detected - system may be unstable");
    systemHealthy = false;
  }
  
  // Reset error flag after 30 seconds
  if (lastCameraError > 0 && (currentTime - lastCameraError) > 30000) {
    lastCameraError = 0;
    systemHealthy = true;
  }
  
  // Check for memory issues - ESP32-S3 has more RAM than original ESP32
  if (ESP.getFreeHeap() < 20000) {  // Adjusted threshold for S3
    Serial.println("Low memory detected");
    systemHealthy = false;
  }
}

bool isSystemResponsive() {
  // Test basic system functions to see if we're truly unresponsive
  unsigned long testStart = millis();
  
  // Only test WiFi if it's been initialized and connected
  if (WiFi.getMode() != WIFI_OFF && WiFi.status() == WL_CONNECTED) {
    // Just verify we can still get WiFi status
    int rssi = WiFi.RSSI();
    if (rssi == 0 || rssi > 0) {
      // WiFi is responding (rssi should be negative, but any response means it works)
    }
  }
  
  // Test memory allocation
  void* testPtr = malloc(100);
  if (testPtr == NULL) {
    return false;  // Can't allocate memory
  }
  free(testPtr);
  
  // Test timer functions
  unsigned long testEnd = millis();
  if (testEnd <= testStart) {
    return false;  // Timer system broken
  }
  
  return true;  // System appears responsive
}

void watchdogReset() {
  Serial.println("Watchdog triggered - system unresponsive!");
  Serial.println("Performing emergency reset...");
  delay(100);
  ESP.restart();
}

void handleHealth() {
  requestCount++;
  lastRequestTime = millis();
  checkSystemHealth();
  
  unsigned long currentTime = millis();
  unsigned long uptime = currentTime - bootTime;
  
  String response = "{";
  response += "\"status\":\"" + String(systemHealthy ? "healthy" : "degraded") + "\",";
  response += "\"uptime\":" + String(uptime) + ",";
  response += "\"freeHeap\":" + String(ESP.getFreeHeap()) + ",";
  response += "\"freePsram\":" + String(ESP.getFreePsram()) + ",";
  response += "\"requestCount\":" + String(requestCount) + ",";
  response += "\"lastActivity\":" + String(lastActivity) + ",";
  response += "\"lastRequest\":" + String(lastRequestTime) + ",";
  response += "\"cameraReady\":" + String(cameraReady ? "true" : "false") + ",";
  response += "\"wifiSSID\":\"" + WiFi.SSID() + "\",";
  response += "\"wifiRSSI\":" + String(WiFi.RSSI()) + ",";
  response += "\"localIP\":\"" + WiFi.localIP().toString() + "\"";
  response += "}";
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Content-Type", "application/json");
  server.send(200, "application/json", response);
}

void handleLED() {
  requestCount++;
  lastRequestTime = millis();
  checkSystemHealth();
  
  ledState = !ledState;
  ledcWrite(LED_PIN, ledState ? 128 : 0);  // 50% brightness when on
  
  String response = ledState ? "ON" : "OFF";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", response);
}

bool initCamera() {
  Serial.println("=== Camera Initialization ===");
  
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
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Print pin configuration for debugging
  Serial.println("Camera Pin Configuration:");
  Serial.printf("  XCLK: %d, PCLK: %d\n", config.pin_xclk, config.pin_pclk);
  Serial.printf("  VSYNC: %d, HREF: %d\n", config.pin_vsync, config.pin_href);
  Serial.printf("  SDA: %d, SCL: %d\n", config.pin_sscb_sda, config.pin_sscb_scl);
  Serial.printf("  PWDN: %d, RESET: %d\n", config.pin_pwdn, config.pin_reset);
  Serial.printf("  Data: Y9=%d Y8=%d Y7=%d Y6=%d Y5=%d Y4=%d Y3=%d Y2=%d\n",
                Y9_GPIO_NUM, Y8_GPIO_NUM, Y7_GPIO_NUM, Y6_GPIO_NUM,
                Y5_GPIO_NUM, Y4_GPIO_NUM, Y3_GPIO_NUM, Y2_GPIO_NUM);

  // Check PSRAM availability - ESP32-S3 typically has 2MB or 8MB PSRAM
  Serial.print("Checking PSRAM... ");
  Serial.println(psramFound() ? "Found" : "Not Found");
  if (psramFound()) {
    Serial.print("  PSRAM size: ");
    Serial.print(ESP.getPsramSize() / 1024 / 1024);
    Serial.println(" MB");
    Serial.print("  Free PSRAM: ");
    Serial.print(ESP.getFreePsram() / 1024 / 1024);
    Serial.println(" MB");
  }
  
  // Configure camera based on PSRAM availability
  if (psramFound()) {
    Serial.println("Configuring camera with PSRAM...");
    config.frame_size = FRAMESIZE_UXGA;    // 1600x1200 with PSRAM
    config.jpeg_quality = 10;              // Better quality
    config.fb_count = 2;                   // Double buffering
    config.grab_mode = CAMERA_GRAB_LATEST; // Always get latest frame
    config.fb_location = CAMERA_FB_IN_PSRAM; // Use PSRAM for frame buffer
  } else {
    Serial.println("No PSRAM detected - using DRAM-only configuration");
    config.frame_size = FRAMESIZE_SVGA;    // 800x600 without PSRAM
    config.jpeg_quality = 12;              // Moderate quality
    config.fb_count = 1;                   // Single buffer to save RAM
    config.fb_location = CAMERA_FB_IN_DRAM; // Use internal DRAM
    config.grab_mode = CAMERA_GRAB_WHEN_EMPTY; // Standard mode
  }

  Serial.println("Initializing camera driver...");
  Serial.println("Attempting to detect camera sensor...");
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("\n!!! ERROR: Camera init failed with error 0x%x !!!\n\n", err);
    
    if (err == ESP_ERR_NOT_SUPPORTED) {
      Serial.println("Camera sensor NOT DETECTED or NOT SUPPORTED");
      Serial.println("\nTroubleshooting steps:");
      Serial.println("1. Check camera module is properly connected");
      Serial.println("2. Verify ribbon cable is fully inserted (contacts facing correct way)");
      Serial.println("3. Check for bent pins on camera connector");
      Serial.println("4. Measure voltage on camera power pins (should be 3.3V)");
      Serial.println("5. Try different camera modules (OV2640, OV3660, OV5640)");
      Serial.println("\nSupported camera sensors:");
      Serial.println("  - OV2640 (most common)");
      Serial.println("  - OV3660");
      Serial.println("  - OV5640");
      Serial.println("  - OV7670 (rarely used)");
      Serial.println("\nPin assignments in use:");
      Serial.printf("  I2C: SDA=%d, SCL=%d (for sensor detection)\n", 
                    config.pin_sscb_sda, config.pin_sscb_scl);
    } else if (err == ESP_ERR_NOT_FOUND) {
      Serial.println("Camera sensor not found on I2C bus");
      Serial.println("Check I2C connections (SDA/SCL pins)");
    } else if (err == ESP_ERR_TIMEOUT) {
      Serial.println("Camera initialization timeout");
      Serial.println("Check XCLK and power supply");
    }
    
    Serial.println("\n=== Camera Initialization FAILED ===\n");
    return false;
  }
  Serial.println("Camera driver initialized successfully");

  // Try to identify the sensor
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    Serial.println("\n=== Camera Sensor Detected ===");
    Serial.printf("Sensor ID: 0x%02X\n", s->id.PID);
    
    // Identify sensor model
    const char* sensorName = "Unknown";
    switch(s->id.PID) {
      case OV2640_PID: sensorName = "OV2640"; break;
      case OV3660_PID: sensorName = "OV3660"; break;
      case OV5640_PID: sensorName = "OV5640"; break;
      case OV7670_PID: sensorName = "OV7670"; break;
      case OV7725_PID: sensorName = "OV7725"; break;
      case NT99141_PID: sensorName = "NT99141"; break;
      case GC2145_PID: sensorName = "GC2145"; break;
      case GC032A_PID: sensorName = "GC032A"; break;
      case GC0308_PID: sensorName = "GC0308"; break;
      case BF3005_PID: sensorName = "BF3005"; break;
      case BF20A6_PID: sensorName = "BF20A6"; break;
      case SC030IOT_PID: sensorName = "SC030IOT"; break;
    }
    Serial.printf("Sensor Model: %s\n", sensorName);
    Serial.println("===============================\n");
    
    // Optimize sensor settings for good quality with reasonable speed
    Serial.println("Configuring camera sensor...");
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    
    // Conservative settings for stability
    s->set_gainceiling(s, GAINCEILING_2X);  // Start conservative
    s->set_quality(s, 12);                  // Moderate quality
    s->set_colorbar(s, 0);                  // Disable test pattern
    s->set_whitebal(s, 1);                  // Enable auto white balance
    s->set_gain_ctrl(s, 1);                 // Enable auto gain control
    s->set_exposure_ctrl(s, 1);             // Enable auto exposure
    s->set_awb_gain(s, 1);                  // Enable AWB gain
    s->set_agc_gain(s, 0);                  // Start with low gain
    s->set_aec_value(s, 300);               // Auto exposure value
    s->set_aec2(s, 0);                      // Disable AEC DSP
    s->set_dcw(s, 1);                       // Enable downsize
    s->set_bpc(s, 0);                       // Disable BPC
    s->set_wpc(s, 1);                       // Enable WPC
    s->set_raw_gma(s, 1);                   // Enable raw gamma
    s->set_lenc(s, 1);                      // Enable lens correction
    s->set_hmirror(s, 0);                   // Disable horizontal mirror
    s->set_vflip(s, 0);                     // Disable vertical flip
    Serial.println("Camera sensor configured");
  } else {
    Serial.println("WARNING: Could not get sensor handle");
  }

  Serial.println("=== Camera Ready ===\n");
  return true;
}

void setup() {
  Serial.begin(115200);
  
  // ESP32-S3 USB CDC needs time to initialize - just use a fixed delay
  delay(2000);
  
  Serial.println("\n\n=== ObsyBox Monitor Camera - ESP32-S3 Freenove Edition ===");
  Serial.println("Firmware starting...");
  
  // Print chip information
  Serial.print("Chip Model: ");
  Serial.println(ESP.getChipModel());
  Serial.print("Chip Revision: ");
  Serial.println(ESP.getChipRevision());
  Serial.print("CPU Frequency: ");
  Serial.print(ESP.getCpuFreqMHz());
  Serial.println(" MHz");
  Serial.print("Flash Size: ");
  Serial.print(ESP.getFlashChipSize() / 1024 / 1024);
  Serial.println(" MB");
  Serial.print("Free Heap: ");
  Serial.print(ESP.getFreeHeap());
  Serial.println(" bytes");
  Serial.print("PSRAM Found: ");
  Serial.println(psramFound() ? "Yes" : "No");
  if (psramFound()) {
    Serial.print("PSRAM Size: ");
    Serial.print(ESP.getPsramSize() / 1024 / 1024);
    Serial.println(" MB");
  }
  Serial.println();

  // Initialize system monitoring
  bootTime = millis();
  lastActivity = bootTime;
  
  // Initialize LED pin
  Serial.println("Initializing flash LED (GPIO 48 with PWM)...");
  ledcAttach(LED_PIN, 5000, 8);  // 5kHz, 8-bit resolution
  ledcWrite(LED_PIN, 0);  // Start with LED off
  Serial.println("Flash LED initialized");

  // Initialize camera
  Serial.println();
  cameraReady = initCamera();
  if (cameraReady) {
    Serial.println("✓ Camera initialized successfully\n");
  } else {
    Serial.println("✗ Camera initialization FAILED\n");
    Serial.println("Continuing without camera...\n");
  }

  // Connect to WiFi network
  Serial.println("=== WiFi Connection ===");
  Serial.print("Connecting to: ");
  Serial.println(SECRET_SSID);
  WiFi.mode(WIFI_STA);
  
  // Configure static IP (adjust for your network)
  IPAddress local_IP(192, 168, 1, 149);  // Change this to your desired IP
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  IPAddress primaryDNS(8, 8, 8, 8);
  IPAddress secondaryDNS(8, 8, 4, 4);
  
  Serial.print("Static IP: ");
  Serial.println(local_IP);
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("WARNING: Static IP configuration failed!");
  }
  
  Serial.print("Connecting");
  WiFi.begin(SECRET_SSID, SECRET_PASS);
  
  // Wait for connection with timeout
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 30000) {
    delay(1000);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Connected!");
    Serial.println("=== WiFi Status ===");
    Serial.print("Network: ");
    Serial.println(WiFi.SSID());
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Gateway: ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.println();
  } else {
    Serial.println(" FAILED!");
    Serial.println("WiFi connection timeout");
    Serial.println("Check credentials in arduino_secrets.h");
    Serial.println("Continuing in offline mode...\n");
  }

  // Start web server
  Serial.println("=== Starting Web Server ===");
  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  server.on("/stream", handleStream);
  server.on("/led", handleLED);
  server.on("/health", handleHealth);
  
  server.begin();
  Serial.println("Web server started on port 80");
  Serial.println();
  Serial.println("========================================");
  Serial.println("  ObsyBox Monitor Camera READY!");
  Serial.println("========================================");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Access at: http://");
    Serial.println(WiFi.localIP());
  }
  Serial.println("========================================");
  Serial.println();
}

void loop() {
  static unsigned long lastWatchdogCheck = 0;
  static unsigned long loopCounter = 0;
  static bool watchdogActive = false;
  
  unsigned long currentTime = millis();
  
  // Don't start watchdog until WiFi is connected and stable
  if (!watchdogActive && WiFi.status() == WL_CONNECTED && currentTime > 60000) {
    watchdogActive = true;
    Serial.println("Watchdog system activated - WiFi connected and system stable");
  }
  
  // Handle web server requests
  server.handleClient();
  
  // Monitor WiFi connection (but don't spam reconnect)
  static unsigned long lastReconnectAttempt = 0;
  // Don't attempt reconnects in first 2 minutes or if already connecting
  if (WiFi.status() != WL_CONNECTED 
      && WiFi.status() != WL_DISCONNECTED  // Not actively connecting
      && currentTime > 120000  // Give 2 minutes after boot
      && currentTime - lastReconnectAttempt > 60000) {  // Only once per minute
    lastReconnectAttempt = currentTime;
    Serial.println("WiFi disconnected - attempting reconnect...");
    WiFi.reconnect();
  }
  
  // Only run watchdog checks after boot delay
  if (watchdogActive && currentTime - lastWatchdogCheck > 5000) {
    lastWatchdogCheck = currentTime;
    
    // Test if system is actually responsive (not just idle)
    if (!isSystemResponsive()) {
      Serial.println("System is truly unresponsive - critical functions failing!");
      watchdogReset();
    } else {
      // System is responsive, just update our "alive" timestamp
      lastActivity = currentTime;
      
      // Check if we've been idle for a long time (for informational purposes)
      if (requestCount > 0 && currentTime - lastRequestTime > 300000) { // 5 minutes
        Serial.println("System idle for " + String((currentTime - lastRequestTime)/60000) + " minutes - but responsive");
      }
    }
    
    // Print system status every 30 seconds
    if (loopCounter % 6 == 0) {
      Serial.println("=== System Status ===");
      Serial.println("Hardware: ESP32-S3 Freenove WROOM");
      Serial.println("Health: " + String(systemHealthy ? "OK" : "DEGRADED"));
      Serial.println("WiFi: " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected"));
      if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Signal: " + String(WiFi.RSSI()) + " dBm");
        Serial.println("IP: " + WiFi.localIP().toString());
      }
      Serial.println("Free Heap: " + String(ESP.getFreeHeap()));
      Serial.println("Free PSRAM: " + String(ESP.getFreePsram()));
      Serial.println("Uptime: " + String((currentTime - bootTime)/1000) + " seconds");
      Serial.println("Requests: " + String(requestCount));
      if (requestCount > 0) {
        Serial.println("Last request: " + String((currentTime - lastRequestTime)/1000) + " seconds ago");
      }
      Serial.println("==================");
    }
    
    loopCounter++;
  }
  
  // Small delay to prevent watchdog timeout
  delay(10);
}
