#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

// Access Point settings
const char *ap_ssid = "ESP32-CAM-AP";
const char *ap_password = ""; // Open network

WebServer server(80);
bool cameraReady = false;

void handleRoot() {
  Serial.println("Root request received");
  String html = "<!DOCTYPE html><html><head><title>ESP32 Debug</title></head><body>";
  html += "<h1>ESP32 Camera Debug</h1>";
  html += "<p>Camera: " + String(cameraReady ? "Ready" : "Failed") + "</p>";
  html += "<p>Free Heap: " + String(ESP.getFreeHeap()) + "</p>";
  html += "<p>Time: " + String(millis()) + "ms</p>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

bool initCamera() {
  Serial.println("Starting camera init...");
  
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

  // Simplified config to avoid memory issues
  config.frame_size = FRAMESIZE_VGA;  // Start smaller
  config.jpeg_quality = 15;           // Lower quality for stability
  config.fb_count = 1;                // Single frame buffer

  Serial.println("Camera config set, calling esp_camera_init...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return false;
  }

  Serial.println("Camera initialized successfully");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);  // Give serial time to initialize
  
  Serial.println("\n\n=== ESP32-CAM Debug Boot ===");
  Serial.printf("Free heap at start: %d bytes\n", ESP.getFreeHeap());
  
  // Try to initialize camera
  Serial.println("Attempting camera initialization...");
  cameraReady = initCamera();
  if (cameraReady) {
    Serial.println("✓ Camera OK");
  } else {
    Serial.println("✗ Camera FAILED - continuing anyway");
  }
  
  Serial.printf("Free heap after camera: %d bytes\n", ESP.getFreeHeap());
  
  // Start Access Point with minimal config
  Serial.println("Starting WiFi AP...");
  WiFi.mode(WIFI_AP);
  bool apStarted = WiFi.softAP(ap_ssid, ap_password);
  
  if (apStarted) {
    Serial.println("✓ WiFi AP started");
    Serial.print("IP address: ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("✗ WiFi AP failed");
  }
  
  // Start web server
  Serial.println("Starting web server...");
  server.on("/", handleRoot);
  server.begin();
  Serial.println("✓ Web server started");
  
  Serial.printf("Final free heap: %d bytes\n", ESP.getFreeHeap());
  Serial.println("=== Boot Complete ===\n");
}

void loop() {
  static unsigned long lastPrint = 0;
  
  server.handleClient();
  
  // Print status every 10 seconds
  if (millis() - lastPrint > 10000) {
    lastPrint = millis();
    Serial.printf("Status: heap=%d, uptime=%ds\n", ESP.getFreeHeap(), millis()/1000);
  }
  
  delay(10);
}