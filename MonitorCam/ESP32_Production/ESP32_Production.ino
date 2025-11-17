#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "arduino_secrets.h"

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

// Watchdog and health monitoring
#define WDT_TIMEOUT 30000  // 30 seconds in milliseconds
unsigned long lastActivity = 0;
unsigned long bootTime = 0;

// LED control
#define LED_PIN 4  // GPIO 4 is the flash LED on AI Thinker ESP32-CAM
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
  html += "<head><title>ObsyBox Monitor Camera</title>";
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
  html += "<h1>ObsyBox Monitor Camera</h1>";
  
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
  
  // Check for memory issues
  if (ESP.getFreeHeap() < 10000) {
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
  digitalWrite(LED_PIN, ledState ? HIGH : LOW);
  
  String response = ledState ? "ON" : "OFF";
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/plain", response);
}

bool initCamera() {
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

  // Check PSRAM availability
  Serial.print("PSRAM found: ");
  Serial.println(psramFound() ? "Yes" : "No");
  if (psramFound()) {
    Serial.print("PSRAM size: ");
    Serial.println(ESP.getPsramSize());
  }
  
  // Optimize for speed over quality
  if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA;   // 800x600
    config.jpeg_quality = 12;             // Lower quality = faster processing
    config.fb_count = 2;                  // Double buffering
    config.grab_mode = CAMERA_GRAB_LATEST; // Always get latest frame
    config.fb_location = CAMERA_FB_IN_PSRAM; // Use PSRAM for frame buffer
  } else {
    Serial.println("WARNING: No PSRAM - using minimal settings");
    config.frame_size = FRAMESIZE_QVGA;   // 320x240 - smallest usable
    config.jpeg_quality = 12;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return false;
  }

  // Optimize sensor settings for speed
  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    
    // Speed optimizations
    s->set_gainceiling(s, GAINCEILING_2X);  // Lower gain ceiling = faster
    s->set_quality(s, 15);                  // Lower quality for speed
    s->set_framesize(s, FRAMESIZE_VGA);     // Ensure VGA size
    s->set_colorbar(s, 0);                  // Disable test pattern
    s->set_whitebal(s, 1);                  // Enable auto white balance
    s->set_gain_ctrl(s, 1);                 // Enable auto gain control
    s->set_exposure_ctrl(s, 1);             // Enable auto exposure
    s->set_awb_gain(s, 1);                  // Enable AWB gain
    s->set_agc_gain(s, 0);                  // Start with low gain
  }

  return true;
}

void setup() {
  Serial.begin(115200);
  Serial.println("Starting ObsyBox Monitor Camera - Deployment Mode");

  // Initialize system monitoring
  bootTime = millis();
  lastActivity = bootTime;
  
  // Initialize LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW); // Start with LED off

  // Initialize camera
  cameraReady = initCamera();
  if (cameraReady) {
    Serial.println("Camera initialized successfully");
  } else {
    Serial.println("Camera initialization failed");
  }

  // Connect to WiFi network
  Serial.println("Connecting to WiFi network...");
  WiFi.mode(WIFI_STA);
  
  // Configure static IP
  IPAddress local_IP(192, 168, 1, 149);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  IPAddress primaryDNS(8, 8, 8, 8);
  IPAddress secondaryDNS(8, 8, 4, 4);
  
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("Static IP configuration failed!");
  }
  
  WiFi.begin(SECRET_SSID, SECRET_PASS);
  
  // Wait for connection with timeout
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 30000) {
    delay(1000);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected successfully!");
    Serial.print("Network: ");
    Serial.println(WiFi.SSID());
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("");
    Serial.println("WiFi connection failed!");
    Serial.println("Check credentials in arduino_secrets.h");
    // Continue anyway - might work locally
  }

  // Start web server
  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  server.on("/stream", handleStream);
  server.on("/led", handleLED);
  server.on("/health", handleHealth);
  
  server.begin();
  Serial.println("Web server started");
  Serial.println("ObsyBox Monitor Camera ready!");
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
      Serial.println("Health: " + String(systemHealthy ? "OK" : "DEGRADED"));
      Serial.println("WiFi: " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected"));
      if (WiFi.status() == WL_CONNECTED) {
        Serial.println("Signal: " + String(WiFi.RSSI()) + " dBm");
        Serial.println("IP: " + WiFi.localIP().toString());
      }
      Serial.println("Free Heap: " + String(ESP.getFreeHeap()));
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