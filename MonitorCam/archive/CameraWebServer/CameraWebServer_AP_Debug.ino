#include "esp_camera.h"
#include <WiFi.h>

//
// WARNING!!! PSRAM IC required for UXGA resolution and high JPEG quality
//            Ensure ESP32 Wrover Module or other board with PSRAM is selected
//            Partial images will be transmitted if image exceeds buffer size
//
//            You must select partition scheme from the board menu that has at least 3MB APP space.

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

// ===========================
// Access Point Configuration
// ===========================
const char *ap_ssid = "ESP32-CAM-AP";           // AP name
const char *ap_password = "12345678";           // AP password (min 8 chars)

// Set AP IP configuration
IPAddress ap_local_IP(192, 168, 4, 1);          // ESP32 IP as AP
IPAddress ap_gateway(192, 168, 4, 1);           // Gateway (same as ESP32 IP)
IPAddress ap_subnet(255, 255, 255, 0);          // Subnet mask

void startCameraServer();
void setupLedFlash(int pin);

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();
  Serial.println("=== ESP32-CAM Access Point Starting ===");

  // Initialize camera with basic settings first
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
  
  // Start with lower resolution to avoid memory issues
  config.frame_size = FRAMESIZE_SVGA;  // 800x600 instead of UXGA
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 15;  // Lower quality = less memory
  config.fb_count = 1;

  // Check PSRAM
  if (psramFound()) {
    Serial.println("PSRAM found - using PSRAM for frame buffer");
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("PSRAM not found - using DRAM (limited resolution)");
    config.frame_size = FRAMESIZE_QVGA;  // 320x240
    config.fb_location = CAMERA_FB_IN_DRAM;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  // Initialize camera
  Serial.println("Initializing camera...");
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    Serial.println("Restarting in 5 seconds...");
    delay(5000);
    ESP.restart();
  }
  Serial.println("Camera initialized successfully!");

  // Get camera sensor and configure
  sensor_t *s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  
  // Set frame size for better performance
  s->set_framesize(s, FRAMESIZE_QVGA);  // Start with small size
  Serial.println("Camera sensor configured");

  // Setup LED Flash if available
#if defined(LED_GPIO_NUM)
  setupLedFlash(LED_GPIO_NUM);
  Serial.println("LED flash configured");
#endif

  // Configure and start Access Point
  Serial.println("Configuring Access Point...");
  
  // Set AP configuration
  if (!WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet)) {
    Serial.println("Failed to configure AP IP settings!");
  }
  
  // Start Access Point
  bool ap_success = WiFi.softAP(ap_ssid, ap_password);
  
  if (ap_success) {
    Serial.println("=== Access Point Started Successfully! ===");
    Serial.print("AP SSID: ");
    Serial.println(ap_ssid);
    Serial.print("AP Password: ");
    Serial.println(ap_password);
    Serial.print("AP IP address: ");
    Serial.println(WiFi.softAPIP());
    Serial.println();
  } else {
    Serial.println("Failed to start Access Point!");
    Serial.println("Restarting in 5 seconds...");
    delay(5000);
    ESP.restart();
  }

  // Start camera web server
  Serial.println("Starting camera web server...");
  startCameraServer();
  Serial.println("=== Camera web server started! ===");
  
  // Final instructions
  Serial.println();
  Serial.println("=== READY TO USE ===");
  Serial.print("1. Connect to WiFi network: '");
  Serial.print(ap_ssid);
  Serial.println("'");
  Serial.print("2. Use password: '");
  Serial.print(ap_password);
  Serial.println("'");
  Serial.print("3. Open browser and go to: http://");
  Serial.println(WiFi.softAPIP());
  Serial.println("=================");
  Serial.println();
}

void loop() {
  // Print status every 30 seconds
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 30000) {
    lastCheck = millis();
    int clients = WiFi.softAPgetStationNum();
    Serial.printf("[STATUS] AP Mode - Clients connected: %d\n", clients);
    Serial.printf("[STATUS] Free heap: %d bytes\n", ESP.getFreeHeap());
    Serial.printf("[STATUS] AP IP: %s\n", WiFi.softAPIP().toString().c_str());
  }
  
  delay(10000);
}