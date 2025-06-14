#include <Wire.h>
#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>

#include "arduino_secrets.h"

// WiFi credentials
const char* ssid = SECRET_SSID; 
const char* password = SECRET_PASS;

// Sensor object
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);

// Web server
AsyncWebServer server(80);

// History buffer for 1 hour (60 samples, 1 per minute)
#define HISTORY_SIZE 60
float luxHistory[HISTORY_SIZE];
int historyIndex = 0;

void addToHistory(float lux) {
  luxHistory[historyIndex] = lux;
  historyIndex = (historyIndex + 1) % HISTORY_SIZE;
}

void setup() {
  Serial.begin(115200);
  Wire.begin(D2, D1); // SDA, SCL for Wemos D1 mini

  // Set static IP
  IPAddress local_IP(192, 168, 1, 100);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  IPAddress dns(8, 8, 8, 8);
  WiFi.config(local_IP, gateway, subnet, dns);

  // WiFi connection
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  // Sensor init
  if (!tsl.begin()) {
    Serial.println("TSL2591 not found. Check wiring!");
    while (1);
  }
  tsl.setGain(TSL2591_GAIN_MED);
  tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);

  // Initialize history array
  for (int i = 0; i < HISTORY_SIZE; i++) {
    luxHistory[i] = NAN;
  }

  // Web server routes
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    String html = R"rawliteral(
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset='utf-8'>
        <title>Sky Condition Sensors</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <meta http-equiv='refresh' content='60'>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
          body { background: #181c24; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; }
          h1 { color: #ffd600; }
          .info { background: #232837; color: #b0b8c0; border-radius: 8px; padding: 10px 18px; max-width: 700px; margin: 18px auto; }
          .values { font-size: 1.2em; margin: 20px 0; }
          .chart-container { width: 95vw; max-width: 700px; margin: 30px auto; background: #232837; border-radius: 8px; padding: 10px; }
        </style>
      </head>
      <body>
        <h1>Sky Condition Sensors</h1>
        <div class='info'>
          <div class='values'>
            <span id="lux"></span>
          </div>
          <div>Last hour history (1 sample/minute):</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px;">
          <div class="chart-container" style="flex:1 1 320px; min-width:280px; max-width:480px;">
            <canvas id="luxChart"></canvas>
          </div>
        </div>
        <div style="margin-top:32px; text-align:center;">
          <small><em>Sensor: TSL2591 (lux)</em></small><br>
          <small id="ssidline"></small>
        </div>
        <script>
          async function fetchData() {
            const res = await fetch('/data');
            return await res.json();
          }
          function minsAgoLabels(count) {
            let arr = [];
            for (let i = count-1; i >= 0; i--) arr.push(i + " min ago");
            return arr;
          }
          function updateValues(data) {
            document.getElementById('lux').innerText = "Lux: " + data.lux_now;
            if (data.ssid && data.rssi !== undefined) {
              document.getElementById('ssidline').innerText = "SSID: " + data.ssid + " (Signal: " + data.rssi + " dBm)";
            }
          }
          fetchData().then(data => {
            updateValues(data);
            let labels = minsAgoLabels(data.lux.length);
            new Chart(document.getElementById('luxChart'), {
              type: 'line',
              data: {
                labels: labels,
                datasets: [{label: 'Lux', data: data.lux, borderColor: 'orange', fill: false}]
              }
            });
          });
          setInterval(() => {
            fetchData().then(data => updateValues(data));
          }, 5000);
        </script>
      </body>
      </html>
    )rawliteral";
    request->send(200, "text/html", html);
  });

  server.on("/data", HTTP_GET, [](AsyncWebServerRequest *request){
    // Prepare JSON with history and current value
    String json = "{";
    json += "\"lux_now\":" + String(luxHistory[(historyIndex + HISTORY_SIZE - 1) % HISTORY_SIZE], 2) + ",";
    json += "\"lux\":[";
    for (int i = 0; i < HISTORY_SIZE; i++) {
      int idx = (historyIndex + i) % HISTORY_SIZE;
      json += isnan(luxHistory[idx]) ? "null" : String(luxHistory[idx], 2);
      if (i < HISTORY_SIZE - 1) json += ",";
    }
    json += "]}";
    request->send(200, "application/json", json);
  });

  server.on("/lux", HTTP_GET, [](AsyncWebServerRequest *request){
    float lux = 0;
    uint32_t lum = tsl.getFullLuminosity();
    uint16_t ir = lum >> 16;
    uint16_t full = lum & 0xFFFF;
    lux = tsl.calculateLux(full, ir);
    request->send(200, "text/plain", String(lux, 2));
  });

  server.begin();
  Serial.println("HTTP server started");
}

// For averaging
#define SAMPLES_PER_MINUTE 10
float luxSum = 0;
int sampleCount = 0;
unsigned long lastSampleTime = 0;
unsigned long lastMinuteTime = 0;

void loop() {
  unsigned long now = millis();

  // Take a sample every 6 seconds (60000 ms / 10)
  if (now - lastSampleTime >= 6000 || lastSampleTime == 0) {
    // Read TSL2591
    uint32_t lum = tsl.getFullLuminosity();
    uint16_t ir = lum >> 16;
    uint16_t full = lum & 0xFFFF;
    float lux = tsl.calculateLux(full, ir);

    // Debug output for each sample
    Serial.print("[Sample] Lux: "); Serial.println(lux, 2);

    luxSum += lux;
    sampleCount++;

    lastSampleTime = now;
  }

  // Every minute, store the average and reset sums
  if ((now - lastMinuteTime >= 60000 && sampleCount > 0) || lastMinuteTime == 0) {
    float avgLux = luxSum / sampleCount;

    addToHistory(avgLux);

    // Debug output for each minute
    Serial.print("[Minute AVG] Lux: "); Serial.println(avgLux, 2);

    // Reset for next minute
    luxSum = 0;
    sampleCount = 0;
    lastMinuteTime = now;
  }
}