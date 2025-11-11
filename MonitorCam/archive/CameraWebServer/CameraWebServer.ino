#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

//
// WARNING!!! PSRAM IC required for UXGA resolution and high JPEG quality
//            Ensure ESP32 Wrover Module or other board with PSRAM is selected
//            Partial images will be transmitted if image exceeds buffer size
//
//            You must select partition scheme from the board menu that has at least 3MB APP space.
//            Face Recognition is DISABLED for ESP32 and ESP32-S2, because it takes up from 15
//            seconds to process single frame. Face Detection is ENABLED if PSRAM is enabled as well

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"
#include "arduino_secrets.h"

// ===========================
// Enter your WiFi credentials
// ===========================
const char *ssid = SECRET_SSID;
const char *password = SECRET_PASS;

// Set your Static IP address
IPAddress local_IP(192, 168, 1, 148);
// Set your Gateway IP address
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

WebServer server(80);
bool cameraReady = false;

WebServer server(80);
bool cameraReady = false;

// Web interface for production use
void handleRoot() {
  String html = "<!DOCTYPE html><html>";
  html += "<head><title>ESP32-CAM ObsyBox</title>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<meta http-equiv='refresh' content='30'>";  // Auto refresh for observatory monitoring
  html += "<style>";
  html += "body{font-family:Arial,sans-serif;margin:20px;background:#f0f0f0;}";
  html += ".container{max-width:800px;margin:0 auto;background:white;padding:20px;border-radius:10px;}";
  html += ".status{background:#e8f5e8;padding:10px;border-radius:5px;margin:10px 0;}";
  html += ".error{background:#ffe8e8;padding:10px;border-radius:5px;margin:10px 0;}";
  html += "button{background:#007bff;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;margin:5px;}";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>ESP32-CAM ObsyBox Monitor</h1>";
  html += "<p><strong>🚀 Production Mode</strong> - Observatory Monitoring System</p>";
  
  // Network status
  html += "<div class='status'>";
  html += "<strong>Network Status:</strong><br>";
  html += "Connected to: " + WiFi.SSID() + "<br>";
  html += "IP: " + WiFi.localIP().toString() + "<br>";
  html += "Signal: " + String(WiFi.RSSI()) + " dBm";
  html += "</div>";
  
  // Camera section
  if (cameraReady) {
    html += "<div class='status'>";
    html += "<strong>📷 AllSky Camera:</strong> Active<br>";
    html += "<img src='/capture' style='max-width:100%;border:1px solid #ddd;border-radius:5px;'><br>";
    html += "<button onclick='location.reload()'>🔄 Refresh View</button>";
    html += "<button onclick='window.open(\"/capture\", \"_blank\")'>🔗 Full Size Image</button>";
    html += "</div>";
  } else {
    html += "<div class='error'>";
    html += "<strong>❌ Camera Status:</strong> Offline";
    html += "</div>";
  }
  
  // System info
  html += "<div class='status'>";
  html += "<strong>System Status:</strong><br>";
  html += "Uptime: " + String(millis()/3600000) + "h " + String((millis()/60000)%60) + "m<br>";
  html += "Free Memory: " + String(ESP.getFreeHeap()/1024) + "KB<br>";
  html += "Last Update: " + String(millis()/1000) + "s";
  html += "</div>";
  
  html += "</div></body></html>";
  
  server.send(200, "text/html", html);
}

void handleCapture() {
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera offline");
    return;
  }
  
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    server.send(503, "text/plain", "Capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
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
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_UXGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  if (psramFound()) {
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return false;
  }

  sensor_t *s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);
    s->set_brightness(s, 1);
    s->set_saturation(s, -2);
  }
  
  s->set_framesize(s, FRAMESIZE_VGA);  // Good balance for AllSky monitoring

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

  return true;
}

void startCameraServer() {
  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  server.begin();
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();
  Serial.println("=== ESP32-CAM ObsyBox Production ===");

  // Initialize camera
  cameraReady = initCamera();
  
  if (cameraReady) {
    Serial.println("Camera initialized successfully!");
  } else {
    Serial.println("Camera initialization failed!");
  }

  // Configure static IP and connect to WiFi
  if(!WiFi.config(local_IP, gateway, subnet)) {
    Serial.println("STA Failed to configure");
  }
  
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");

  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
}

void loop() {
  server.handleClient();
  
  // Status check every 30 seconds
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 30000) {
    lastCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected - attempting reconnect");
      WiFi.reconnect();
    } else {
      Serial.printf("Status OK - IP: %s, Camera: %s, Heap: %d\n",
                    WiFi.localIP().toString().c_str(),
                    cameraReady ? "OK" : "FAIL",
                    ESP.getFreeHeap());
    }
  }
  
  delay(100);
}
