#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

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

// Static IP configuration
IPAddress staticIP(192, 168, 1, 124);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

DHT dht(DHTPIN, DHTTYPE);
ESP8266WebServer server(80);

// Data storage for 30 minutes (sampled every minute)
#define HISTORY_SIZE 30
float tempHistory[HISTORY_SIZE];
float humHistory[HISTORY_SIZE];
float anemometerHistory[HISTORY_SIZE]; 
int historyIndex = 0;
unsigned long lastSampleTime = 0;

// Add these global variables to store the latest averages
float lastAvgTemperature = NAN;
float lastAvgHumidity = NAN;
float lastAvgAnemometer = NAN;

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
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body { font-family: sans-serif; }
        .chart-container { width: 90vw; max-width: 700px; margin: 30px auto; }
      </style>
    </head>
    <body>
      <h1>Current Readings</h1>
      <p>Temperature: )rawliteral" + String(temperature, 1) + R"rawliteral(&deg;C</p>
      <p>Humidity: )rawliteral" + String(humidity, 1) + R"rawliteral( %</p>
      <p>Wind Speed (ADC): )rawliteral" + String(windspeed, 1) + R"rawliteral(</p>
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
    anemometerHistory[i] = NAN; // <-- Add this line
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

  server.on("/", handleRoot);
  server.on("/temperature", handleTemperature);
  server.on("/humidity", handleHumidity);
  server.on("/windspeed", handleWindspeed);
  server.on("/data", handleData);
  server.begin();
}

void loop() {
  server.handleClient();

  unsigned long now = millis();
  // Sample every minute
  if (now - lastSampleTime > 60000 || lastSampleTime == 0) {
    const int NUM_SAMPLES = 5;
    float humiditySum = 0;
    float temperatureSum = 0;
    int anemometerSum = 0;
    int validSamples = 0;

    for (int i = 0; i < NUM_SAMPLES; i++) {
      float h = dht.readHumidity();
      float t = dht.readTemperature();
      int a = analogRead(ANEMOMETER_PIN);
      if (!isnan(h) && !isnan(t)) {
        humiditySum += h;
        temperatureSum += t;
        anemometerSum += a;
        validSamples++;
      }
      delay(200); // Short delay between samples
    }

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

    lastSampleTime = now;
  }
}