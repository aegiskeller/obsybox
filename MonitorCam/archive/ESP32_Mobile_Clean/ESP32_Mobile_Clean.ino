#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ===================
// Select camera model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
#include "camera_pins.h"

const char* ssid = "ESP32-CAM-AP";
const char* password = "12345678";

WebServer server(80);

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // Boost CPU frequency for better performance
  setCpuFrequencyMhz(240);

  // Initialize LED pins
  pinMode(4, OUTPUT);  // Flash LED
  pinMode(33, OUTPUT); // Builtin LED
  digitalWrite(4, LOW);
  digitalWrite(33, LOW);

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
  config.xclk_freq_hz = 8000000;   // Even slower clock for maximum stability
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;  // Wait for empty buffer

  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;      // Smaller frame size to prevent overflow
    config.jpeg_quality = 15;               // Higher compression, smaller files
    config.fb_count = 4;                    // Maximum buffers for overflow protection
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_QQVGA;     // Very small for limited memory
    config.jpeg_quality = 20;               // High compression
    config.fb_count = 2;                    // Dual buffer
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Conservative camera sensor settings for stability
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    s->set_framesize(s, FRAMESIZE_QVGA);      // Start with small, stable size
    s->set_quality(s, 15);                    // High compression to prevent overflow
    s->set_brightness(s, 0);                  // Neutral settings initially
    s->set_contrast(s, 0);                    // Neutral contrast
    s->set_saturation(s, 0);                  // Neutral saturation
    s->set_sharpness(s, 0);                   // No additional processing
    s->set_denoise(s, 0);                     // Disable all extra processing
    s->set_gainceiling(s, GAINCEILING_4X);    // Very low gain to prevent large frames
    s->set_agc_gain(s, 5);                    // Minimal gain
    s->set_aec_value(s, 300);                 // Short exposure
    s->set_aec2(s, 0);                        // Disable AEC2
    s->set_ae_level(s, 0);                    // Minimal auto exposure
    s->set_awb_gain(s, 1);                    // Auto white balance gain
    s->set_wb_mode(s, 0);                     // Auto white balance
    s->set_hmirror(s, 0);                     // No horizontal mirror
    s->set_vflip(s, 0);                       // No vertical flip
    s->set_lenc(s, 1);                        // Keep lens correction
    s->set_raw_gma(s, 0);                     // Disable gamma
    s->set_dcw(s, 0);                         // Disable cropping
    s->set_bpc(s, 0);                         // Disable bad pixel correction
    s->set_wpc(s, 0);                         // Disable white pixel correction
  }

  WiFi.softAP(ssid);  // Open network (no password)
  Serial.println("Access Point Started");
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());

  server.on("/", handleRoot);
  server.on("/capture", handleCapture);
  server.on("/stream", handleStream);
  server.on("/mobile_stream", handleMobileStream);
  server.on("/toggle_led", handleToggleLED);
  server.on("/toggle_night", handleToggleNight);
  server.on("/set_resolution", handleSetResolution);
  server.on("/set_quality", handleSetQuality);
  server.on("/set_brightness", handleSetBrightness);
  server.on("/set_contrast", handleSetContrast);
  server.onNotFound(handle404);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}

void handleCORS() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.sendHeader("Pragma", "no-cache");
  server.sendHeader("Expires", "0");
}

void handle404() {
  handleCORS();
  server.send(404, "text/plain", "Not found");
}

void handleRoot() {
  handleCORS();
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta charset='UTF-8'>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<title>ObsyBox Monitor</title>";
  html += "<style>";
  html += "body { margin: 0; padding: 20px; background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%); color: #00ff00; font-family: 'Courier New', monospace; min-height: 100vh; }";
  html += ".container { max-width: 800px; margin: 0 auto; text-align: center; }";
  html += "h1 { color: #00ff00; text-shadow: 0 0 10px #00ff00; margin-bottom: 30px; }";
  html += ".image-container { margin: 20px 0; padding: 10px; border: 2px solid #00ff00; border-radius: 10px; background: rgba(0,255,0,0.1); }";
  html += "#camera_image { max-width: 90vw; min-width: 300px; height: auto; border-radius: 5px; background: #000; }";
  html += ".controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }";
  html += ".control-group { background: rgba(0,255,0,0.1); padding: 15px; border-radius: 10px; border: 1px solid #00ff00; }";
  html += "button { background: #0a0a0a; color: #00ff00; border: 2px solid #00ff00; padding: 10px 15px; margin: 5px; border-radius: 5px; cursor: pointer; font-family: inherit; transition: all 0.3s; }";
  html += "button:hover { background: #00ff00; color: #000; box-shadow: 0 0 15px #00ff00; }";
  html += "select, input { background: #0a0a0a; color: #00ff00; border: 2px solid #00ff00; padding: 8px; margin: 5px; border-radius: 5px; font-family: inherit; }";
  html += ".info { background: rgba(0,255,0,0.05); padding: 15px; border-radius: 10px; border: 1px solid #333; margin: 20px 0; }";
  html += "@media (max-width: 600px) { .controls { grid-template-columns: 1fr; } #camera_image { min-width: 250px; } }";
  html += "</style></head><body>";
  
  html += "<div class='container'>";
  html += "<h1>ObsyBox Monitor</h1>";
  
  html += "<div class='image-container'>";
  html += "<img id='camera_image' src='/capture' alt='Camera Feed' ";
  html += "onload='console.log(\"Image loaded successfully\");' ";
  html += "onerror='console.error(\"Failed to load image\"); this.src=\"data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDMwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiMwMDAiLz48dGV4dCB4PSIxNTAiIHk9IjEwMCIgZm9udC1mYW1pbHk9Im1vbm9zcGFjZSIgZm9udC1zaXplPSIxNiIgZmlsbD0iIzAwZmYwMCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+Q2FtZXJhIE5vdCBBdmFpbGFibGU8L3RleHQ+PC9zdmc+\";' />";
  html += "<p style='color: #888; margin-top: 10px;' id='stream_status'>Click Stream for live video or Capture for single image</p>";
  html += "</div>";

  html += "<div class='controls'>";
  html += "<div class='control-group'>";
  html += "<h3>Camera Controls</h3>";
  html += "<button onclick='captureImage()'>Capture</button>";
  html += "<button onclick='startStream()'>Stream</button>";
  html += "<button onclick='stopStream()'>Stop</button>";
  html += "<button onclick='toggleLED()' id='led_btn'>Toggle LED</button>";
  html += "<button onclick='toggleNightMode()' id='night_btn'>Night Mode</button>";
  html += "</div>";

  html += "<div class='control-group'>";
  html += "<h3>Resolution</h3>";
  html += "<select id='resolution' onchange='setResolution()'>";
  html += "<option value='0'>96x96</option>";
  html += "<option value='1'>QQVGA (160x120)</option>";
  html += "<option value='2'>QCIF (176x144)</option>";
  html += "<option value='3' selected>HQVGA (240x176)</option>";
  html += "<option value='4'>240x240</option>";
  html += "<option value='5'>QVGA (320x240)</option>";
  html += "<option value='6'>CIF (400x296)</option>";
  html += "<option value='7'>HVGA (480x320)</option>";
  html += "<option value='8'>VGA (640x480)</option>";
  html += "<option value='9'>SVGA (800x600)</option>";
  html += "<option value='10'>XGA (1024x768)</option>";
  html += "<option value='11'>HD (1280x720)</option>";
  html += "<option value='12'>SXGA (1280x1024)</option>";
  html += "<option value='13'>UXGA (1600x1200)</option>";
  html += "</select>";
  html += "</div>";

  html += "<div class='control-group'>";
  html += "<h3>Settings</h3>";
  html += "<label>Quality: <input type='range' min='10' max='63' value='10' id='quality' onchange='setQuality(this.value)'></label><br>";
  html += "<label>Brightness: <input type='range' min='-2' max='2' value='0' id='brightness' onchange='setBrightness(this.value)'></label><br>";
  html += "<label>Contrast: <input type='range' min='-2' max='2' value='0' id='contrast' onchange='setContrast(this.value)'></label>";
  html += "</div></div>";

  html += "<div class='info'>";
  html += "<p>📡 Access Point: ESP32-CAM-AP</p>";
  html += "<p>🌐 IP: 192.168.4.1</p>";
  html += "<p>🔋 Status: Active</p>";
  html += "</div></div>";

  html += "<script>";
  html += "let streaming = false;";
  html += "let autoRefresh = null;";
  html += "let streamInterval = null;";
  html += "let isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);";
  html += "function captureImage() { ";
  html += "  if (!streaming) {";
  html += "    document.getElementById('camera_image').src = '/capture?' + new Date().getTime();";
  html += "    document.getElementById('stream_status').textContent = 'Single capture mode';";
  html += "  }";
  html += "}";
  html += "function startStream() {";
  html += "  if (!streaming) {";
  html += "    streaming = true;";
  html += "    clearInterval(autoRefresh);";
  html += "    if (isMobile) {";
  html += "      // Mobile fallback: rapid capture mode";
  html += "      document.getElementById('stream_status').textContent = 'Mobile stream active (~3 FPS)';";
  html += "      streamInterval = setInterval(function() {";
  html += "        if (streaming) document.getElementById('camera_image').src = '/capture?' + new Date().getTime();";
  html += "      }, 333);";  // ~3 FPS for mobile
  html += "    } else {";
  html += "      // Desktop: real MJPEG stream";
  html += "      document.getElementById('camera_image').src = '/stream?' + new Date().getTime();";
  html += "      document.getElementById('stream_status').textContent = 'Desktop stream active (~5 FPS)';";
  html += "    }";
  html += "  }";
  html += "}";
  html += "function stopStream() {";
  html += "  streaming = false;";
  html += "  clearInterval(streamInterval);";
  html += "  document.getElementById('stream_status').textContent = 'Stream stopped - switching to capture mode';";
  html += "  setTimeout(captureImage, 500);";
  html += "  autoRefresh = setInterval(captureImage, 5000);";
  html += "}";
  html += "function toggleLED() { fetch('/toggle_led'); }";
  html += "function toggleNightMode() { fetch('/toggle_night'); }";
  html += "function setResolution() { ";
  html += "  fetch('/set_resolution?value=' + document.getElementById('resolution').value);";
  html += "  setTimeout(function() { if (streaming) startStream(); else captureImage(); }, 1000);";
  html += "}";
  html += "function setQuality(val) { fetch('/set_quality?value=' + val); }";
  html += "function setBrightness(val) { fetch('/set_brightness?value=' + val); }";
  html += "function setContrast(val) { fetch('/set_contrast?value=' + val); }";
  html += "autoRefresh = setInterval(captureImage, 5000);";
  html += "document.getElementById('camera_image').onclick = function() { if (!streaming) captureImage(); };";
  html += "</script></body></html>";
  
  server.send(200, "text/html", html);
}

void handleCapture() {
  handleCORS();
  
  // Clear any existing frame buffer issues
  esp_camera_fb_return(esp_camera_fb_get());
  delay(50);
  
  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.sendHeader("Content-Length", String(fb->len));
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.sendHeader("Pragma", "no-cache");
  server.sendHeader("Expires", "0");
  server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
  
  esp_camera_fb_return(fb);
}

void handleStream() {
  handleCORS();
  server.sendHeader("Content-Type", "multipart/x-mixed-replace; boundary=frame");
  server.sendHeader("Cache-Control", "no-cache, no-store, must-revalidate");
  server.sendHeader("Pragma", "no-cache");
  server.sendHeader("Expires", "0");
  server.send(200);
  
  WiFiClient client = server.client();
  static uint8_t buffer[1024];
  
  // Clear any pending frame buffers before starting stream
  camera_fb_t * clear_fb = esp_camera_fb_get();
  if (clear_fb) esp_camera_fb_return(clear_fb);
  
  while (client.connected()) {
    camera_fb_t * fb = esp_camera_fb_get();
    if (fb) {
      // Check frame size to prevent overflow issues
      if (fb->len > 0 && fb->len < 100000) {  // Sanity check frame size
        // Send frame header efficiently
        client.print("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ");
        client.print(fb->len);
        client.print("\r\n\r\n");
        
        // Send image data in chunks for better performance
        size_t remaining = fb->len;
        uint8_t *buf_ptr = fb->buf;
        
        while (remaining > 0 && client.connected()) {
          size_t chunk_size = (remaining > sizeof(buffer)) ? sizeof(buffer) : remaining;
          size_t written = client.write(buf_ptr, chunk_size);
          if (written != chunk_size) break;
          buf_ptr += chunk_size;
          remaining -= chunk_size;
        }
        
        client.print("\r\n");
      }
      esp_camera_fb_return(fb);
      
      // Much slower frame rate for buffer stability
      delay(200); // ~5 FPS (very conservative for stability)
    } else {
      delay(300); // Wait longer if no frame available
    }
  }
}

void handleToggleLED() {
  handleCORS();
  static bool ledState = false;
  ledState = !ledState;
  digitalWrite(4, ledState);
  digitalWrite(33, ledState);
  server.send(200, "text/plain", ledState ? "LED ON" : "LED OFF");
}

void handleSetResolution() {
  handleCORS();
  if (server.hasArg("value")) {
    int val = server.arg("value").toInt();
    sensor_t * s = esp_camera_sensor_get();
    if (s) {
      framesize_t sizes[] = {
        FRAMESIZE_96X96,    // 0
        FRAMESIZE_QQVGA,    // 1
        FRAMESIZE_QCIF,     // 2
        FRAMESIZE_HQVGA,    // 3
        FRAMESIZE_240X240,  // 4
        FRAMESIZE_QVGA,     // 5
        FRAMESIZE_CIF,      // 6
        FRAMESIZE_HVGA,     // 7
        FRAMESIZE_VGA,      // 8
        FRAMESIZE_SVGA,     // 9
        FRAMESIZE_XGA,      // 10
        FRAMESIZE_HD,       // 11
        FRAMESIZE_SXGA,     // 12
        FRAMESIZE_UXGA      // 13
      };
      if (val >= 0 && val <= 13) {
        s->set_framesize(s, sizes[val]);
        server.send(200, "text/plain", "Resolution set to " + String(val));
        return;
      }
    }
  }
  server.send(400, "text/plain", "Invalid resolution");
}

void handleSetQuality() {
  handleCORS();
  if (server.hasArg("value")) {
    int val = server.arg("value").toInt();
    if (val >= 10 && val <= 63) {
      sensor_t * s = esp_camera_sensor_get();
      if (s) {
        s->set_quality(s, val);
        server.send(200, "text/plain", "Quality set to " + String(val));
        return;
      }
    }
  }
  server.send(400, "text/plain", "Invalid quality");
}

void handleSetBrightness() {
  handleCORS();
  if (server.hasArg("value")) {
    int val = server.arg("value").toInt();
    if (val >= -2 && val <= 2) {
      sensor_t * s = esp_camera_sensor_get();
      if (s) {
        s->set_brightness(s, val);
        server.send(200, "text/plain", "Brightness set to " + String(val));
        return;
      }
    }
  }
  server.send(400, "text/plain", "Invalid brightness");
}

void handleSetContrast() {
  handleCORS();
  if (server.hasArg("value")) {
    int val = server.arg("value").toInt();
    if (val >= -2 && val <= 2) {
      sensor_t * s = esp_camera_sensor_get();
      if (s) {
        s->set_contrast(s, val);
        server.send(200, "text/plain", "Contrast set to " + String(val));
        return;
      }
    }
  }
  server.send(400, "text/plain", "Invalid contrast");
}

void handleToggleNight() {
  handleCORS();
  static bool nightMode = false;  // Start in day mode for stability
  nightMode = !nightMode;
  
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    if (nightMode) {
      // Low light / night mode settings (conservative to prevent overflow)
      s->set_quality(s, 12);                    // Moderate quality to prevent overflow
      s->set_brightness(s, 2);                  // More brightness boost
      s->set_contrast(s, 2);                    // Higher contrast
      s->set_saturation(s, -2);                 // Lower saturation for sensitivity
      s->set_gainceiling(s, GAINCEILING_64X);   // High but not maximum gain
      s->set_agc_gain(s, 25);                   // High gain
      s->set_aec_value(s, 900);                 // Longer exposure
      s->set_aec2(s, 1);                        // Enable AEC2
      s->set_ae_level(s, 2);                    // High exposure level
      s->set_denoise(s, 1);                     // Enable denoise
      s->set_raw_gma(s, 1);                     // Enable gamma correction
      s->set_bpc(s, 1);                         // Bad pixel correction
      s->set_wpc(s, 1);                         // White pixel correction
      server.send(200, "text/plain", "Night Mode ON - Enhanced low light");
    } else {
      // Day mode / normal settings
      s->set_quality(s, 10);                    // Normal quality
      s->set_brightness(s, 1);                  // Slight brightness
      s->set_contrast(s, 1);                    // Slight contrast
      s->set_saturation(s, -1);                 // Slight desaturation
      s->set_gainceiling(s, GAINCEILING_16X);   // Normal gain
      s->set_agc_gain(s, 15);                   // Moderate gain
      s->set_aec_value(s, 600);                 // Normal exposure
      s->set_aec2(s, 0);                        // Disable AEC2
      s->set_ae_level(s, 1);                    // Normal exposure level
      s->set_denoise(s, 0);                     // Disable denoise for speed
      s->set_raw_gma(s, 0);                     // Disable gamma correction
      s->set_bpc(s, 0);                         // Disable bad pixel correction
      s->set_wpc(s, 0);                         // Disable white pixel correction
      server.send(200, "text/plain", "Day Mode ON - Stable settings");
    }
  } else {
    server.send(500, "text/plain", "Camera sensor not available");
  }
}

void handleMobileStream() {
  // Simple capture endpoint optimized for mobile rapid refresh
  handleCapture();
}