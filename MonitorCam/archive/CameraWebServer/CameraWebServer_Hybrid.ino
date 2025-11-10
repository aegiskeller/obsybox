#include "esp_camera.h"
#include <WiFi.h>

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
//#define CAMERA_MODEL_WROVER_KIT // Has PSRAM
//#define CAMERA_MODEL_ESP_EYE  // Has PSRAM
//#define CAMERA_MODEL_ESP32S3_EYE // Has PSRAM
//#define CAMERA_MODEL_M5STACK_PSRAM // Has PSRAM
//#define CAMERA_MODEL_M5STACK_V2_PSRAM // M5Camera version B Has PSRAM
//#define CAMERA_MODEL_M5STACK_WIDE // Has PSRAM
//#define CAMERA_MODEL_M5STACK_ESP32CAM // No PSRAM
//#define CAMERA_MODEL_M5STACK_UNITCAM // No PSRAM
//#define CAMERA_MODEL_M5STACK_CAMS3_UNIT  // Has PSRAM
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
//#define CAMERA_MODEL_TTGO_T_JOURNAL // No PSRAM
//#define CAMERA_MODEL_XIAO_ESP32S3 // Has PSRAM
// ** Espressif Internal Boards **
//#define CAMERA_MODEL_ESP32_CAM_BOARD
//#define CAMERA_MODEL_ESP32S2_CAM_BOARD
//#define CAMERA_MODEL_ESP32S3_CAM_LCD
//#define CAMERA_MODEL_DFRobot_FireBeetle2_ESP32S3 // Has PSRAM
//#define CAMERA_MODEL_DFRobot_Romeo_ESP32S3 // Has PSRAM
#include "camera_pins.h"
#include "arduino_secrets.h"

// ===========================
// Network Configuration
// ===========================
// WiFi Station Mode Credentials
const char *ssid = SECRET_SSID;
const char *password = SECRET_PASS;

// Set your Static IP address for Station Mode
IPAddress local_IP(192, 168, 1, 148);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

// Access Point Configuration (fallback)
const char *ap_ssid = "ESP32-CAM-AP";           // AP name
const char *ap_password = "12345678";           // AP password (min 8 chars)
IPAddress ap_local_IP(192, 168, 4, 1);          // ESP32 IP as AP
IPAddress ap_gateway(192, 168, 4, 1);           // Gateway (same as ESP32 IP)
IPAddress ap_subnet(255, 255, 255, 0);          // Subnet mask

// Connection timeout in milliseconds
const unsigned long WIFI_TIMEOUT = 20000;       // 20 seconds

bool isAPMode = false;                           // Track current mode

void startCameraServer();
void setupLedFlash(int pin);

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

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
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t *s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // flip it back
    s->set_brightness(s, 1);   // up the brightness just a bit
    s->set_saturation(s, -2);  // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  if (config.pixel_format == PIXFORMAT_JPEG) {
    s->set_framesize(s, FRAMESIZE_QVGA);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash(LED_GPIO_NUM);
#endif

  // First try to connect to WiFi
  Serial.println("Trying to connect to WiFi...");
  
  // Configure static IP
  if(!WiFi.config(local_IP, gateway, subnet)) {
    Serial.println("STA Failed to configure");
  }
  
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  unsigned long startAttemptTime = millis();
  
  // Wait for connection with timeout
  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < WIFI_TIMEOUT) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    // Successfully connected to WiFi
    Serial.println("");
    Serial.println("WiFi connected successfully!");
    Serial.print("Camera Ready! Use 'http://");
    Serial.print(WiFi.localIP());
    Serial.println("' to connect");
    isAPMode = false;
  } else {
    // WiFi connection failed, start Access Point
    Serial.println("");
    Serial.println("WiFi connection failed. Starting Access Point...");
    
    // Stop WiFi client mode
    WiFi.disconnect();
    
    // Configure and start Access Point
    WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet);
    bool ap_success = WiFi.softAP(ap_ssid, ap_password);
    
    if (ap_success) {
      Serial.println("Access Point started successfully!");
      Serial.print("AP SSID: ");
      Serial.println(ap_ssid);
      Serial.print("AP Password: ");
      Serial.println(ap_password);
      Serial.print("Camera Ready! Use 'http://");
      Serial.print(WiFi.softAPIP());
      Serial.println("' to connect");
      Serial.println("Connect your device to the AP network to access the camera");
      isAPMode = true;
    } else {
      Serial.println("Failed to start Access Point!");
      return;
    }
  }

  startCameraServer();
}

void loop() {
  if (isAPMode) {
    // In AP mode, show connected clients info
    static unsigned long lastClientCheck = 0;
    if (millis() - lastClientCheck > 30000) {
      lastClientCheck = millis();
      int clients = WiFi.softAPgetStationNum();
      Serial.printf("AP Mode - Clients connected: %d\n", clients);
    }
  } else {
    // In Station mode, check WiFi connection
    static unsigned long lastWiFiCheck = 0;
    if (millis() - lastWiFiCheck > 30000) {
      lastWiFiCheck = millis();
      if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi connection lost!");
        // Could implement reconnection logic here
      } else {
        Serial.printf("Station Mode - WiFi connected, IP: %s\n", WiFi.localIP().toString().c_str());
      }
    }
  }
  
  delay(10000);
}