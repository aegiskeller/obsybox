#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <FS.h> // Include the SPIFFS library
#include <PubSubClient.h>
#include <Ticker.h>  // For ESP8266 watchdog

// --- Add min/max values for plotting ---
float tmin = 0, tmax = 60;      // Temperature range (°C)
float hmin = 0, hmax = 100;     // Humidity range (%)
float amin = 0, amax = 1023;    // Anemometer ADC range

#define DHTPIN 4
#define DHTTYPE DHT22
#define ANEMOMETER_PIN A0
#define DHT_POWER_PIN 5  // Optional: Connect DHT VCC to this pin for power cycling

// Sensor health tracking
unsigned long lastSuccessfulRead = 0;
int consecutiveFailures = 0;
const int MAX_CONSECUTIVE_FAILURES = 5;

#include "arduino_secrets.h"
// WiFi credentials - support multiple networks
struct WiFiNetwork {
  const char* ssid;
  const char* password;
};

WiFiNetwork wifiNetworks[] = {
  {SECRET_SSID_1, SECRET_PASS_1},
  {SECRET_SSID_2, SECRET_PASS_2},
  {SECRET_SSID_3, SECRET_PASS_3}
};
const int numNetworks = sizeof(wifiNetworks) / sizeof(wifiNetworks[0]);
String connectedSSID = "";

// MQTT settings
const char* mqtt_server = "192.168.1.49";
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/anemometer";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// Static IP configuration
IPAddress staticIP(192, 168, 1, 183);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

// AP mode configuration
const char* ap_ssid = "Wombat-Weather";
const char* ap_password = "obsybox123";
IPAddress apIP(192, 168, 4, 1);
IPAddress apGateway(192, 168, 4, 1);
IPAddress apSubnet(255, 255, 255, 0);
bool apMode = false;

DHT dht(DHTPIN, DHTTYPE);
ESP8266WebServer server(80);

// Data storage (sampled every minute)
#define HISTORY_SIZE 60
float tempHistory[HISTORY_SIZE];
float humHistory[HISTORY_SIZE];
float anemometerHistory[HISTORY_SIZE]; 
int historyIndex = 0;
unsigned long lastSampleTime = 0;

// Add these global variables to store the latest averages
float lastAvgTemperature = NAN;
float lastAvgHumidity = NAN;
float lastAvgAnemometer = NAN;

// Non-blocking MQTT reconnect variables
unsigned long lastMqttReconnectAttempt = 0;
const unsigned long mqttReconnectInterval = 5000; // 5 seconds between attempts

// Watchdog variables
Ticker watchdogTicker;
const int WATCHDOG_TIMEOUT = 60; // seconds
unsigned long lastWatchdogReset = 0;
bool watchdogEnabled = false;

// Function to reset the device after watchdog timeout
void resetModule() {
  Serial.println("Watchdog timeout - resetting device!");
  ESP.restart();
}

// Feed the watchdog to prevent reset
void feedWatchdog() {
  if (watchdogEnabled) {
    lastWatchdogReset = millis();
  }
}

// Robust sensor reading with validation
bool readDHTWithRetry(float &temp, float &hum, int maxRetries = 3) {
  for (int attempt = 0; attempt < maxRetries; attempt++) {
    if (attempt > 0) {
      delay(2000); // DHT22 needs 2 seconds between reads
      Serial.print("Retry #");
      Serial.println(attempt);
    }
    
    temp = dht.readTemperature();
    hum = dht.readHumidity();
    
    // Validate readings - DHT22 ranges: -40 to 80°C, 0-100% RH
    if (!isnan(temp) && !isnan(hum) && 
        temp >= -40 && temp <= 80 && 
        hum >= 0 && hum <= 100) {
      consecutiveFailures = 0;
      lastSuccessfulRead = millis();
      return true;
    }
  }
  
  consecutiveFailures++;
  Serial.print("DHT read failed. Consecutive failures: ");
  Serial.println(consecutiveFailures);
  
  // Power cycle DHT if available and too many failures
  if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
    Serial.println("Too many failures - attempting sensor power cycle");
    // Uncomment if you wire DHT VCC to DHT_POWER_PIN
    // digitalWrite(DHT_POWER_PIN, LOW);
    // delay(1000);
    // digitalWrite(DHT_POWER_PIN, HIGH);
    // delay(2000);
    // dht.begin();
    consecutiveFailures = 0;
  }
  
  return false;
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("Anemometer_ESP8266")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void handleRoot() {
  // Get latest values, or use fallback if NaN
  float temperature = isnan(lastAvgTemperature) ? 
    tempHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE] : lastAvgTemperature;
  float humidity = isnan(lastAvgHumidity) ? 
    humHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE] : lastAvgHumidity;
  float windspeed = isnan(lastAvgAnemometer) ? 
    anemometerHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE] : lastAvgAnemometer;
  
  // If still NaN, show placeholder text
  String tempStr = isnan(temperature) ? "waiting for data..." : String(temperature, 1);
  String humStr = isnan(humidity) ? "waiting for data..." : String(humidity, 1);
  String windStr = isnan(windspeed) ? "waiting for data..." : String(windspeed, 1);

  String modeInfo = apMode ? 
    "Mode: Access Point (AP)<br>AP SSID: " + String(ap_ssid) + "<br>AP IP: " + apIP.toString() :
    "Mode: Station (STA)<br>WiFi SSID: " + connectedSSID + "<br>Static IP: " + staticIP.toString();

  String html = R"rawliteral(
  <!DOCTYPE html>
  <html>
  <head>
    <meta charset='utf-8'>
    <title>Weather Station</title>
    <meta http-equiv='refresh' content='60'>
    <link rel="icon" type="image/png" href="data:image/png;base64,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">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
      body {
        font-family: sans-serif;
        background: #181c24;
        color: #e0e0e0;
      }
      .chart-container { width: 90vw; max-width: 700px; margin: 30px auto; }
      .info {
        font-size: 0.95em;
        font-style: italic;
        margin: 18px auto 18px auto;
        max-width: 700px;
        background: #232837;
        color: #b0b8c0;
        border-radius: 8px;
        padding: 10px 18px;
        line-height: 1.5;
        text-align: left;
      }
      a { color: #80bfff; }
      canvas { background: #232837; border-radius: 8px; }
    </style>
  </head>
  <body>
    <h1>Wombat Weather Station</h1>
    <h2>Current Readings</h2>
    <p>Temperature: )rawliteral" + tempStr + R"rawliteral(&deg;C</p>
    <p>Humidity: )rawliteral" + humStr + R"rawliteral( %</p>
    <p>Wind Speed (ADC): )rawliteral" + windStr + R"rawliteral(</p>
    <div class="info">
      <em>
        ESP8266 weather station with DHT22 sensor and anemometer.<br>
        Data sampled every minute, displayed in real-time.<br>
        Last updated: )rawliteral" + String(millis() / 1000) + R"rawliteral( seconds ago.<br>
        )rawliteral" + modeInfo + R"rawliteral(<br>
        Firmware: 1.0.0, History: 60 min, 100 samples/min.<br>
        Charts below show the last 60 minutes of data.
      </em>
    </div>
    <div class="chart-container"><canvas id="tempChart"></canvas></div>
    <div class="chart-container"><canvas id="humChart"></canvas></div>
    <div class="chart-container"><canvas id="windChart"></canvas></div>
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
      fetchData().then(data => {
        let labels = minsAgoLabels(data.temperature.length);
        new Chart(document.getElementById('tempChart'), {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{label: 'Temperature (°C)', data: data.temperature, borderColor: 'red', fill: false}]
          }
        });
        new Chart(document.getElementById('humChart'), {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{label: 'Humidity (%)', data: data.humidity, borderColor: 'blue', fill: false}]
          }
        });
        new Chart(document.getElementById('windChart'), {
          type: 'line',
          data: {
            labels: labels,
            datasets: [{label: 'Wind Speed (ADC)', data: data.windspeed, borderColor: 'green', fill: false}]
          }
        });
      });
    </script>
  </body>
  </html>
  )rawliteral";

  server.send(200, "text/html", html);
}

void handleTemperature() {
  if (isnan(lastAvgTemperature)) {
    server.send(200, "text/plain", "NaN");
  } else {
    server.send(200, "text/plain", String(lastAvgTemperature, 2));
  }
}

void handleHumidity() {
  if (isnan(lastAvgHumidity)) {
    server.send(200, "text/plain", "NaN");
  } else {
    server.send(200, "text/plain", String(lastAvgHumidity, 2));
  }
}

void handleWindspeed() {
  if (isnan(lastAvgAnemometer)) {
    server.send(200, "text/plain", "NaN");
  } else {
    server.send(200, "text/plain", String(lastAvgAnemometer, 2));
  }
}

void handleData() {
  String json = "{";
  json += "\"temperature\":[";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(tempHistory[idx])) json += String(tempHistory[idx], 2); else json += "null";
    if (i < HISTORY_SIZE - 1) json += ",";
  }
  json += "],\"humidity\":[";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(humHistory[idx])) json += String(humHistory[idx], 2); else json += "null";
    if (i < HISTORY_SIZE - 1) json += ",";
  }
  json += "],\"windspeed\":[";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(anemometerHistory[idx])) json += String(anemometerHistory[idx], 2); else json += "null";
    if (i < HISTORY_SIZE - 1) json += ",";
  }
  json += "]}";
  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  
  // Optional: Set up DHT power pin for power cycling capability
  // pinMode(DHT_POWER_PIN, OUTPUT);
  // digitalWrite(DHT_POWER_PIN, HIGH);
  // delay(2000); // Give sensor time to stabilize
  
  dht.begin();
  delay(2000); // DHT22 needs time to stabilize on startup

  // Initialize history arrays
  for (int i = 0; i < HISTORY_SIZE; i++) {
    tempHistory[i] = NAN;
    humHistory[i] = NAN;
    anemometerHistory[i] = NAN;
  }

  // Scan for available networks and connect to strongest
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  
  Serial.println("Scanning for WiFi networks...");
  int n = WiFi.scanNetworks();
  
  int bestNetwork = -1;
  int bestRSSI = -100;
  
  if (n > 0) {
    Serial.print(n);
    Serial.println(" networks found");
    
    // Check each scanned network against our known networks
    for (int i = 0; i < n; i++) {
      String scannedSSID = WiFi.SSID(i);
      int rssi = WiFi.RSSI(i);
      
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(scannedSSID);
      Serial.print(" (");
      Serial.print(rssi);
      Serial.println(" dBm)");
      
      // Check if this is one of our configured networks
      for (int j = 0; j < numNetworks; j++) {
        if (scannedSSID == String(wifiNetworks[j].ssid)) {
          if (rssi > bestRSSI) {
            bestRSSI = rssi;
            bestNetwork = j;
          }
        }
      }
    }
  }
  
  // Try to connect to the best network found
  if (bestNetwork >= 0) {
    Serial.print("Connecting to strongest network: ");
    Serial.print(wifiNetworks[bestNetwork].ssid);
    Serial.print(" (");
    Serial.print(bestRSSI);
    Serial.println(" dBm)");
    
    WiFi.config(staticIP, gateway, subnet);
    WiFi.begin(wifiNetworks[bestNetwork].ssid, wifiNetworks[bestNetwork].password);
    connectedSSID = String(wifiNetworks[bestNetwork].ssid);
    
    unsigned long wifiStartTime = millis();
    while (WiFi.status() != WL_CONNECTED) {
      if (millis() - wifiStartTime > 300000) { // 5 minute timeout
        Serial.println("\nWiFi connection timeout. Starting Access Point mode...");
        apMode = true;
        break;
      }
      delay(500);
      Serial.print(".");
      yield(); // Feed the ESP8266 watchdog
    }
  } else {
    Serial.println("No known networks found. Starting Access Point mode...");
    apMode = true;
  }

  // Enable watchdog timer BEFORE starting AP/Station mode
  watchdogTicker.attach(WATCHDOG_TIMEOUT, resetModule);
  watchdogEnabled = true;
  lastWatchdogReset = millis();
  Serial.println("Watchdog timer enabled");

  if (apMode) {
    // Start AP mode
    WiFi.mode(WIFI_AP);
    WiFi.softAPConfig(apIP, apGateway, apSubnet);
    WiFi.softAP(ap_ssid, ap_password);
    Serial.println("\nAccess Point started");
    Serial.print("AP SSID: ");
    Serial.println(ap_ssid);
    Serial.print("AP Password: ");
    Serial.println(ap_password);
    Serial.print("AP IP address: ");
    Serial.println(WiFi.softAPIP());
    feedWatchdog(); // Feed watchdog after AP setup
  } else {
    Serial.println("\nWiFi connected in Station mode");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    // Only connect to MQTT if in Station mode
    mqttClient.setServer(mqtt_server, mqtt_port);
    feedWatchdog(); // Feed watchdog after network setup
  }

  server.on("/", handleRoot);
  server.on("/temperature", handleTemperature);
  server.on("/humidity", handleHumidity);
  server.on("/windspeed", handleWindspeed);
  server.on("/data", handleData);
  server.serveStatic("/favicon.png", SPIFFS, "/favicon.png"); // Serve the favicon
  server.begin();
}

void loop() {
  // Feed the watchdog to prevent reset
  feedWatchdog();

  server.handleClient();

  // Non-blocking MQTT reconnection (only in Station mode)
  if (!apMode) {
    if (!mqttClient.connected()) {
      unsigned long now = millis();
      if (now - lastMqttReconnectAttempt > mqttReconnectInterval) {
        lastMqttReconnectAttempt = now;
        Serial.print("Attempting MQTT connection...");
        if (mqttClient.connect("Anemometer_ESP8266")) {
          Serial.println("connected");
        } else {
          Serial.print("failed, rc=");
          Serial.print(mqttClient.state());
          Serial.println(" will try again in 5 seconds");
        }
      }
    }
    mqttClient.loop();
  }

  // Rest of the loop code is unchanged
  static unsigned long lastSampleTime = 0;
  static unsigned long sampleStartTime = 0;
  static int sampleCount = 0;
  static float humiditySum = 0;
  static float temperatureSum = 0;
  static int anemometerSum = 0;
  static int validSamples = 0;
  static const int NUM_SAMPLES = 100;
  static unsigned long lastSampleInterval = 0;
  static unsigned long lastMqttPublish = 0;

  unsigned long now = millis();

  // --- Print sensor values every 10 seconds for debugging ---
  static unsigned long lastDebugPrint = 0;
  if (now - lastDebugPrint >= 10000 || lastDebugPrint == 0) {
    float h, t;
    bool success = readDHTWithRetry(t, h, 2);
    int a = analogRead(ANEMOMETER_PIN);
    Serial.print("[DEBUG] Raw Sensor Readings - Temp: ");
    Serial.print(success ? String(t, 2) : "NaN");
    Serial.print(" °C, Humidity: ");
    Serial.print(success ? String(h, 2) : "NaN");
    Serial.print(" %, Anemometer ADC: ");
    Serial.print(a);
    Serial.print(" [Status: ");
    Serial.print(success ? "OK" : "FAIL");
    Serial.println("]");
    lastDebugPrint = now;
  }

  // Start a new averaging cycle every minute
  if ((now - lastSampleTime > 60000 || lastSampleTime == 0) && sampleCount == 0) {
    sampleStartTime = now;
    sampleCount = 0;
    humiditySum = 0;
    temperatureSum = 0;
    anemometerSum = 0;
    validSamples = 0;
    lastSampleInterval = 0;
  }

  // Take samples every 600ms until NUM_SAMPLES is reached (DHT22 needs 2s between reads)
  if (sampleCount < NUM_SAMPLES && (now - lastSampleInterval >= 2100) && (sampleStartTime != 0)) {
    float h, t;
    int a = analogRead(ANEMOMETER_PIN);
    
    // Use retry logic but only 1 retry during sampling to not block too long
    if (readDHTWithRetry(t, h, 1)) {
      humiditySum += h;
      temperatureSum += t;
      anemometerSum += a;
      validSamples++;
    } else {
      // Still count the attempt, just don't add to sum
      Serial.println("[WARN] Skipping invalid sample");
    }
    sampleCount++;
    lastSampleInterval = now;
  }

  // When enough samples have been taken, calculate averages and store
  if (sampleCount == NUM_SAMPLES && sampleStartTime != 0) {
    float avgHumidity = validSamples > 0 ? humiditySum / validSamples : NAN;
    float avgTemperature = validSamples > 0 ? temperatureSum / validSamples : NAN;
    float avgAnemometer = validSamples > 0 ? (float)anemometerSum / validSamples : NAN;

    // Only store if we got at least 50% valid samples
    if (validSamples >= NUM_SAMPLES / 2) {
      tempHistory[historyIndex] = avgTemperature;
      humHistory[historyIndex] = avgHumidity;
      anemometerHistory[historyIndex] = avgAnemometer; 
      historyIndex = (historyIndex + 1) % HISTORY_SIZE;

      // Store latest averages for API endpoints
      lastAvgTemperature = avgTemperature;
      lastAvgHumidity = avgHumidity;
      lastAvgAnemometer = avgAnemometer;
    } else {
      Serial.print("[WARN] Insufficient valid samples (");
      Serial.print(validSamples);
      Serial.print("/");
      Serial.print(NUM_SAMPLES);
      Serial.println("), keeping previous values");
    }

    Serial.print("[SAMPLE] Temperature: ");
    Serial.print(isnan(avgTemperature) ? "NaN" : String(avgTemperature, 2));
    Serial.print(" °C, Humidity: ");
    Serial.print(isnan(avgHumidity) ? "NaN" : String(avgHumidity, 2));
    Serial.print(" %, Anemometer ADC: ");
    Serial.print(isnan(avgAnemometer) ? "NaN" : String(avgAnemometer, 2));
    Serial.print(" [Valid: ");
    Serial.print(validSamples);
    Serial.print("/");
    Serial.print(NUM_SAMPLES);
    Serial.println("]");

    // --- MQTT publish every minute (after averaging) - only in Station mode ---
    if (!apMode && mqttClient.connected() && validSamples >= NUM_SAMPLES / 2) {
      if (!isnan(avgTemperature) && !isnan(avgHumidity) && !isnan(avgAnemometer)) {
        char payload[128];
        snprintf(payload, sizeof(payload),
          "{\"t\":%.2f,\"h\":%.2f,\"ws\":%.2f}",
          avgTemperature, avgHumidity, avgAnemometer);
        bool published = mqttClient.publish(mqtt_topic, payload);
        Serial.print("MQTT publish: ");
        Serial.println(published ? "SUCCESS" : "FAILED");
      } else {
        Serial.println("[WARN] Skipping MQTT publish - invalid data");
      }
    }

    lastSampleTime = now;
    sampleStartTime = 0;
    sampleCount = 0;
  }
}