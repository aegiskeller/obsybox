#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <FS.h> // Include the SPIFFS library
#include <PubSubClient.h> 

// --- Add min/max values for plotting ---
float tmin = 0, tmax = 40;      // Temperature range (°C)
float hmin = 0, hmax = 100;     // Humidity range (%)
float amin = 0, amax = 1023;    // Anemometer ADC range

#define DHTPIN 4
#define DHTTYPE DHT22
#define ANEMOMETER_PIN A0

#include "arduino_secrets.h"
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

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
  float temperature = tempHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE];
  float humidity = humHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE];
  float windspeed = lastAvgAnemometer;

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
    <p>Temperature: )rawliteral" + String(temperature, 1) + R"rawliteral(&deg;C</p>
    <p>Humidity: )rawliteral" + String(humidity, 1) + R"rawliteral( %</p>
    <p>Wind Speed (ADC): )rawliteral" + String(windspeed, 1) + R"rawliteral(</p>
    <div class="info">
      <em>
        ESP8266 weather station with DHT22 sensor and anemometer.<br>
        Data sampled every minute, displayed in real-time.<br>
        Last updated: )rawliteral" + String(millis() / 1000) + R"rawliteral( seconds ago.<br>
        Static IP: )rawliteral" + staticIP.toString() + R"rawliteral(<br>
        WiFi SSID: )rawliteral" + String(ssid) + R"rawliteral(<br>
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
  server.send(200, "text/plain", String(lastAvgTemperature, 2));
}

void handleHumidity() {
  server.send(200, "text/plain", String(lastAvgHumidity, 2));
}

void handleWindspeed() {
  server.send(200, "text/plain", String(lastAvgAnemometer, 2));
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
  dht.begin();

  // Initialize history arrays
  for (int i = 0; i < HISTORY_SIZE; i++) {
    tempHistory[i] = NAN;
    humHistory[i] = NAN;
    anemometerHistory[i] = NAN;
  }

  WiFi.mode(WIFI_STA);
  WiFi.config(staticIP, gateway, subnet);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  mqttClient.setServer(mqtt_server, mqtt_port); 
  server.on("/", handleRoot);
  server.on("/temperature", handleTemperature);
  server.on("/humidity", handleHumidity);
  server.on("/windspeed", handleWindspeed);
  server.on("/data", handleData);
  server.serveStatic("/favicon.png", SPIFFS, "/favicon.png"); // Serve the favicon
  server.begin();
}

void loop() {
  server.handleClient();

  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

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

  // Take samples every 500ms until NUM_SAMPLES is reached
  if (sampleCount < NUM_SAMPLES && (now - lastSampleInterval >= 500) && (sampleStartTime != 0)) {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    int a = analogRead(ANEMOMETER_PIN);
    if (!isnan(h) && !isnan(t)) {
      humiditySum += h;
      temperatureSum += t;
      anemometerSum += a;
      validSamples++;
    }
    sampleCount++;
    lastSampleInterval = now;
  }

  // When enough samples have been taken, calculate averages and store
  if (sampleCount == NUM_SAMPLES && sampleStartTime != 0) {
    float avgHumidity = validSamples > 0 ? humiditySum / validSamples : NAN;
    float avgTemperature = validSamples > 0 ? temperatureSum / validSamples : NAN;
    float avgAnemometer = validSamples > 0 ? (float)anemometerSum / validSamples : NAN;

    tempHistory[historyIndex] = avgTemperature;
    humHistory[historyIndex] = avgHumidity;
    anemometerHistory[historyIndex] = avgAnemometer; 
    historyIndex = (historyIndex + 1) % HISTORY_SIZE;

    // Store latest averages for API endpoints
    lastAvgTemperature = avgTemperature;
    lastAvgHumidity = avgHumidity;
    lastAvgAnemometer = avgAnemometer;

    Serial.print("Temperature: ");
    Serial.print(avgTemperature);
    Serial.print(" °C, Humidity: ");
    Serial.print(avgHumidity);
    Serial.print(" %, Anemometer ADC: ");
    Serial.println(avgAnemometer);

    // --- MQTT publish every minute (after averaging) ---
    char payload[128];
    snprintf(payload, sizeof(payload),
      "{\"t\":%.2f,\"h\":%.2f,\"ws\":%.2f}",
      avgTemperature, avgHumidity, avgAnemometer);
    mqttClient.publish(mqtt_topic, payload);

    lastSampleTime = now;
    sampleStartTime = 0;
    sampleCount = 0;
  }
}