#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <math.h>

// Pin definitions
#define DHTPIN 5        // DHT11 data pin connected to NodeMCU D2
#define DHTTYPE DHT11   // DHT 11
#define LIGHT_SENSOR_PIN A0 // Light sensor connected to analog pin A0

// WiFi credentials
#include "arduino_secrets.h"
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)
// define a fixed ip
IPAddress local_ip(192, 168, 1, 184); // Set a fixed IP address
IPAddress gateway(192, 168, 1, 1);    // Set the gateway IP address
IPAddress subnet(255, 255, 255, 0);   // Set the subnet mask
IPAddress dns(192, 168, 1, 1);        // Set the DNS server IP address
// Initialize DHT sensor
DHT dht(DHTPIN, DHTTYPE);
// use an async web server
AsyncWebServer server(80);
// Variables to store sensor data
float temperature = 0.0;
float humidity = 0.0;
int lightLevel = 0;   

#define HISTORY_SIZE 120
float tempHistory[HISTORY_SIZE];
float humHistory[HISTORY_SIZE];
float lightHistory[HISTORY_SIZE];
float dewHistory[HISTORY_SIZE];
int historyIndex = 0;

// Function prototype for calculateDewPoint
float calculateDewPoint(float tempC, float hum);

// Function to read sensor data
void readSensors() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int l = analogRead(LIGHT_SENSOR_PIN);

  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }
  temperature = t;
  humidity = h;
  lightLevel = l;

  // Update history arrays
  tempHistory[historyIndex] = temperature;
  humHistory[historyIndex] = humidity;
  lightHistory[historyIndex] = lightLevel;
  dewHistory[historyIndex] = calculateDewPoint(temperature, humidity);
  historyIndex = (historyIndex + 1) % HISTORY_SIZE;

  Serial.print("Temperature: ");
  Serial.print(t);
  Serial.print(" C, Humidity: ");
  Serial.print(h);
  Serial.print(" %, Light Level: ");
  Serial.print(l);
  Serial.println();
}

// Function to handle root URL
void handleRoot(AsyncWebServerRequest *request) {
  String html = R"rawliteral(
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset='utf-8'>
      <title>Weather Sensor Data</title>
      <meta http-equiv='refresh' content='60'>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body { font-family: sans-serif; }
        .chart-container { width: 90vw; max-width: 700px; margin: 30px auto; }
      </style>
    </head>
    <body>
      <h1>Weather Sensor Data</h1>
      <p>Temperature: )rawliteral" + String(temperature, 1) + R"rawliteral( C</p>
      <p>Humidity: )rawliteral" + String(humidity, 1) + R"rawliteral( %</p>
      <p>Light Level: )rawliteral" + String(lightLevel) + R"rawliteral(</p>
      <p>Dew Point: )rawliteral" + String(calculateDewPoint(temperature, humidity), 1) + R"rawliteral( C</p>
      <div class="chart-container"><canvas id="tempChart"></canvas></div>
      <div class="chart-container"><canvas id="humChart"></canvas></div>
      <div class="chart-container"><canvas id="lightChart"></canvas></div>
      <script>
        async function fetchHistory() {
          const res = await fetch('/data');
          return await res.json();
        }
        function minsAgoLabels(count) {
          let arr = [];
          for (let i = count-1; i >= 0; i--) arr.push(i + " min ago");
          return arr;
        }
        fetchHistory().then(data => {
          let labels = minsAgoLabels(data.temperature.length);
          // Temperature + Dew Point on same chart
          new Chart(document.getElementById('tempChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [
                {label: 'Temperature (°C)', data: data.temperature, borderColor: 'red', fill: false},
                {label: 'Dew Point (°C)', data: data.dewpoint, borderColor: 'green', fill: false}
              ]
            }
          });
          // Humidity chart
          new Chart(document.getElementById('humChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{label: 'Humidity (%)', data: data.humidity, borderColor: 'blue', fill: false}]
            }
          });
          // Light chart
          new Chart(document.getElementById('lightChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{label: 'Light', data: data.light, borderColor: 'orange', fill: false}]
            }
          });
        });
      </script>
    </body>
    </html>
  )rawliteral";
  request->send(200, "text/html", html);
} 

// Function to handle sensor data in JSON format
void handleSensorData(AsyncWebServerRequest *request) {
  String json = "{";
  json += "\"temperature\": " + String(temperature) + ",";
  json += "\"humidity\": " + String(humidity) + ",";
  json += "\"lightLevel\": " + String(lightLevel);
  json += "}";
  request->send(200, "application/json", json);
}

// Function to handle historical data in JSON format
void handleData(AsyncWebServerRequest *request) {
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
  json += "],\"light\":[";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(lightHistory[idx])) json += String(lightHistory[idx], 2); else json += "null";
    if (i < HISTORY_SIZE - 1) json += ",";
  }
  json += "],\"dewpoint\":[";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(dewHistory[idx])) json += String(dewHistory[idx], 2); else json += "null";
    if (i < HISTORY_SIZE - 1) json += ",";
  }
  json += "]}";
  request->send(200, "application/json", json);
}

// Function to handle not found requests
void handleNotFound(AsyncWebServerRequest *request) {
  request->send(404, "text/plain", "Not Found");
}

// Setup function
void setup() {
  // Start Serial communication for debugging
  Serial.begin(115200);
  // Initialize DHT sensor
  dht.begin();
  // Connect to WiFi
  WiFi.config(local_ip, gateway, subnet, dns);
  WiFi.begin(ssid, pass);
  // Wait for connection
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  // Set up web server routes
  server.on("/", HTTP_GET, handleRoot);
  server.on("/sensor-data", HTTP_GET, handleSensorData);
  server.on("/data", HTTP_GET, handleData);
  server.onNotFound(handleNotFound);
  // Start the server
  server.begin();
  Serial.println("HTTP server started");

  for (int i = 0; i < HISTORY_SIZE; i++) {
    tempHistory[i] = NAN;
    humHistory[i] = NAN;
    lightHistory[i] = NAN;
    dewHistory[i] = NAN;
  }
  historyIndex = 0;
  // Initialize sensor data
  temperature = 0.0;
  humidity = 0.0;
  lightLevel = 0;
}

// Loop function
void loop() {
  static unsigned long lastSampleTime = 0;
  static unsigned long sampleStartTime = 0;
  static int sampleCount = 0;
  static float humiditySum = 0;
  static float temperatureSum = 0;
  static int lightSum = 0;
  static float dewSum = 0;
  static int validSamples = 0;
  static const int NUM_SAMPLES = 100;
  static unsigned long lastSampleInterval = 0;

  unsigned long now = millis();

  // Start a new averaging cycle every minute
  if ((now - lastSampleTime > 60000 || lastSampleTime == 0) && sampleCount == 0) {
    sampleStartTime = now;
    sampleCount = 0;
    humiditySum = 0;
    temperatureSum = 0;
    lightSum = 0;
    dewSum = 0;
    validSamples = 0;
    lastSampleInterval = 0;
  }

  // Take samples every 500ms until NUM_SAMPLES is reached
  if (sampleCount < NUM_SAMPLES && (now - lastSampleInterval >= 500) && (sampleStartTime != 0)) {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    int l = analogRead(LIGHT_SENSOR_PIN);
    float d = calculateDewPoint(t, h);
    if (!isnan(h) && !isnan(t)) {
      humiditySum += h;
      temperatureSum += t;
      lightSum += l;
      dewSum += d;
      validSamples++;
    }
    sampleCount++;
    lastSampleInterval = now;
  }

  // When enough samples have been taken, calculate averages and store
  if (sampleCount == NUM_SAMPLES && sampleStartTime != 0) {
    float avgHumidity = validSamples > 0 ? humiditySum / validSamples : NAN;
    float avgTemperature = validSamples > 0 ? temperatureSum / validSamples : NAN;
    float avgLight = validSamples > 0 ? (float)lightSum / validSamples : NAN;
    float avgDew = validSamples > 0 ? dewSum / validSamples : NAN;

    tempHistory[historyIndex] = avgTemperature;
    humHistory[historyIndex] = avgHumidity;
    lightHistory[historyIndex] = avgLight;
    dewHistory[historyIndex] = avgDew;
    historyIndex = (historyIndex + 1) % HISTORY_SIZE;

    // Optionally store latest averages for API endpoints
    temperature = avgTemperature;
    humidity = avgHumidity;
    lightLevel = avgLight;

    Serial.print("Temperature: ");
    Serial.print(avgTemperature);
    Serial.print(" °C, Humidity: ");
    Serial.print(avgHumidity);
    Serial.print(" %, Light: ");
    Serial.print(avgLight);
    Serial.print(", Dew Point: ");
    Serial.println(avgDew);

    lastSampleTime = now;
    sampleStartTime = 0;
    sampleCount = 0;
  }
}

float calculateDewPoint(float tempC, float hum) {
  // Magnus formula
  double a = 17.62, b = 243.12;
  double gamma = log(hum / 100.0) + (a * tempC) / (b + tempC);
  return (b * gamma) / (a - gamma);
}
