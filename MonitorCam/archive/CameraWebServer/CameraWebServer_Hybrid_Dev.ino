#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "arduino_secrets.h"

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

// ===================
// DEVELOPMENT MODE SWITCH
// ===================
// Set to true for AP mode (development), false for home network (production)
#define DEVELOPMENT_MODE true

// Home Network Configuration (production mode)
const char *home_ssid = SECRET_SSID;
const char *home_password = SECRET_PASS;
IPAddress home_local_IP(192, 168, 1, 148);
IPAddress home_gateway(192, 168, 1, 1);
IPAddress home_subnet(255, 255, 255, 0);

// Access Point Configuration (development mode)
const char *ap_ssid = "ESP32-CAM-DEV";
const char *ap_password = "12345678";
IPAddress ap_local_IP(192, 168, 4, 1);
IPAddress ap_gateway(192, 168, 4, 1);
IPAddress ap_subnet(255, 255, 255, 0);

WebServer server(80);
bool cameraReady = false;
bool isAPMode = false;

// Web interface with development features
void handleRoot() {
  String html = "<!DOCTYPE html><html>";
  html += "<head><title>ESP32-CAM ObsyBox</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<style>";
  html += "body{font-family:Arial,sans-serif;margin:20px;background:#f0f0f0;}";
  html += ".container{max-width:800px;margin:0 auto;background:white;padding:20px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}";
  html += ".status{background:#e8f5e8;padding:10px;border-radius:5px;margin:10px 0;}";
  html += ".error{background:#ffe8e8;padding:10px;border-radius:5px;margin:10px 0;}";
  html += "button{background:#007bff;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;margin:5px;}";
  html += "button:hover{background:#0056b3;}";
  html += ".dev-mode{background:#fff3cd;border:1px solid #ffeaa7;padding:10px;border-radius:5px;margin:10px 0;}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>ESP32-CAM ObsyBox Monitor</h1>";
  
  // Development mode indicator
  if (isAPMode) {
    html += "<div class='dev-mode'>";
    html += "<strong>🔧 DEVELOPMENT MODE</strong><br>";
    html += "Currently running as Access Point for testing and development";
    html += "</div>";
  }
  
  // Network status
  html += "<div class='status'>";
  html += "<strong>Network Status:</strong><br>";
  if (isAPMode) {
    html += "Mode: Access Point (Development)<br>";
    html += "SSID: " + String(ap_ssid) + "<br>";
    html += "IP: " + WiFi.softAPIP().toString() + "<br>";
    html += "Connected clients: " + String(WiFi.softAPgetStationNum());
  } else {
    html += "Mode: Station (Production)<br>";
    html += "Connected to: " + WiFi.SSID() + "<br>";
    html += "IP: " + WiFi.localIP().toString() + "<br>";
    html += "Signal strength: " + String(WiFi.RSSI()) + " dBm";
  }
  html += "</div>";
  
  // Camera section
  if (cameraReady) {
    html += "<div class='status'>";
    html += "<strong>📷 Camera Status:</strong> Ready<br>";
    html += "<img src='/capture' style='max-width:100%;border:1px solid #ddd;border-radius:5px;margin:10px 0;'><br>";
    html += "<button onclick='refreshImage()'>📸 Capture New Image</button>";
    html += "<button onclick='window.open(\"/capture\", \"_blank\")'>🔗 Open Image in New Tab</button>";
    html += "</div>";
  } else {
    html += "<div class='error'>";
    html += "<strong>❌ Camera Status:</strong> Not Available";
    html += "</div>";
  }
  
  // System info
  html += "<div class='status'>";
  html += "<strong>System Info:</strong><br>";
  html += "Free heap: " + String(ESP.getFreeHeap()) + " bytes<br>";
  html += "Uptime: " + String(millis()/1000) + " seconds<br>";
  html += "Flash size: " + String(ESP.getFlashChipSize()) + " bytes<br>";
  html += "PSRAM: " + String(psramFound() ? "Available" : "Not found");
  html += "</div>";
  
  // Development controls
  if (isAPMode) {
    html += "<div class='dev-mode'>";
    html += "<strong>🔧 Development Controls:</strong><br>";
    html += "<button onclick='location.reload()'>🔄 Refresh Page</button>";
    html += "<button onclick='if(confirm(\"Restart ESP32?\"))fetch(\"/restart\")'>🔄 Restart Device</button>";
    html += "</div>";
  }
  
  // Auto-refresh script
  html += "<script>";
  html += "function refreshImage(){document.querySelector('img').src='/capture?t='+Date.now();}";
  html += "setInterval(refreshImage, 30000);"; // Auto-refresh image every 30 seconds
  html += "</script>";
  
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
  Serial.println("Served main page");
}

void handleCapture() {
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera not available");
    return;
  }
  
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(503, "text/plain", "Camera capture failed");
    Serial.println("Camera capture failed!");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
  Serial.printf("Image served (%d bytes)\n", fb->len);
}

void handleRestart() {
  server.send(200, "text/plain", "Restarting...");
  delay(1000);
  ESP.restart();
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
  config.frame_size = FRAMESIZE_QVGA;  // Start small
  config.jpeg_quality = 15;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  
  if (psramFound()) {
    Serial.println("PSRAM found - using for frame buffer");
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    Serial.println("PSRAM not found - using DRAM");
    config.fb_location = CAMERA_FB_IN_DRAM;
  }
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return false;
  }
  
  // Configure camera sensor
  sensor_t * s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_VGA);  // 640x480 for good balance
  
  Serial.println("Camera initialized successfully!");
  return true;
}

void setupNetwork() {
  if (DEVELOPMENT_MODE) {
    // Development mode - Access Point
    Serial.println("=== DEVELOPMENT MODE - Starting Access Point ===");
    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet);
    
    if (WiFi.softAP(ap_ssid, ap_password)) {
      Serial.println("Access Point started successfully!");
      Serial.print("SSID: ");
      Serial.println(ap_ssid);
      Serial.print("Password: ");
      Serial.println(ap_password);
      Serial.print("IP: ");
      Serial.println(WiFi.softAPIP());
      isAPMode = true;
    } else {
      Serial.println("Failed to start Access Point!");
    }
  } else {
    // Production mode - Connect to home network
    Serial.println("=== PRODUCTION MODE - Connecting to Home Network ===");
    WiFi.mode(WIFI_STA);
    
    if (!WiFi.config(home_local_IP, home_gateway, home_subnet)) {
      Serial.println("STA Failed to configure");
    }
    
    WiFi.begin(home_ssid, home_password);
    WiFi.setSleep(false);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
      delay(1000);
      Serial.print(".");
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("");
      Serial.println("Connected to home network!");
      Serial.print("IP: ");
      Serial.println(WiFi.localIP());
      isAPMode = false;
    } else {
      Serial.println("");
      Serial.println("Failed to connect to home network - falling back to AP mode");
      // Fallback to AP mode
      WiFi.mode(WIFI_AP);
      WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet);
      WiFi.softAP(ap_ssid, ap_password);
      isAPMode = true;
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== ESP32-CAM ObsyBox Monitor ===");
  
  // Setup network first
  setupNetwork();
  
  // Initialize camera
  cameraReady = initCamera();
  if (cameraReady) {
    Serial.println("Camera ready!");
  } else {
    Serial.println("Camera failed - continuing without camera");
  }
  
  // Setup web server routes
  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  if (isAPMode) {
    server.on("/restart", handleRestart);  // Only in development mode
  }
  
  server.begin();
  Serial.println("Web server started!");
  
  if (isAPMode) {
    Serial.println("🔧 DEVELOPMENT MODE READY 🔧");
    Serial.println("Connect to '" + String(ap_ssid) + "' and go to http://192.168.4.1");
  } else {
    Serial.println("🚀 PRODUCTION MODE READY 🚀");
    Serial.println("Access via http://" + WiFi.localIP().toString());
  }
  Serial.println("=====================================");
}

void loop() {
  server.handleClient();
  
  static unsigned long lastStatus = 0;
  if (millis() - lastStatus > 30000) {
    lastStatus = millis();
    
    if (isAPMode) {
      Serial.printf("[DEV] Clients: %d, Heap: %d, Camera: %s\n", 
                    WiFi.softAPgetStationNum(), 
                    ESP.getFreeHeap(),
                    cameraReady ? "OK" : "FAIL");
    } else {
      Serial.printf("[PROD] WiFi: %s, IP: %s, Heap: %d, Camera: %s\n",
                    WiFi.status() == WL_CONNECTED ? "OK" : "DISCONNECTED",
                    WiFi.localIP().toString().c_str(),
                    ESP.getFreeHeap(),
                    cameraReady ? "OK" : "FAIL");
    }
  }
  
  delay(100);
}