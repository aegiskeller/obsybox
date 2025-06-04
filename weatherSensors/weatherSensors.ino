#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <math.h>

// Pin definitions
#define DHTPIN 2        // DHT11 data pin connected to NodeMCU D4 
#define DHTTYPE DHT11   // DHT 11
#define LIGHT_SENSOR_PIN A0 // Light sensor connected to analog pin A0

#define READ_INTERVAL 60000 // ms
#define HISTORY_DURATION 1800000UL // 1/2 hour in ms
#define HISTORY_SIZE (HISTORY_DURATION / READ_INTERVAL)
// WiFi credentials
#include "arduino_secrets.h"
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)

struct SensorReading {
  float temperature;
  float humidity;
  int lightValue;
  unsigned long timestamp;
};

SensorReading history[HISTORY_SIZE];
int historyIndex = 0;
int historyCount = 0;

DHT dht(DHTPIN, DHTTYPE);
ESP8266WebServer server(80);

// Dew point calculation function (Magnus formula)
float calculateDewPoint(float tempC, float humidity) {
  // Constants for Magnus formula
  const float a = 17.62;
  const float b = 243.12;
  float gamma = log(humidity / 100.0) + (a * tempC) / (b + tempC);
  return (b * gamma) / (a - gamma);
}

// Function prototypes
void handleRoot();
void handleData();

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(LIGHT_SENSOR_PIN, INPUT);

  // Connect to WiFi with static IP
  IPAddress local_IP(192, 168, 1, 123);      // Set your desired static IP
  IPAddress gateway(192, 168, 1, 1);         // Set your network gateway
  IPAddress subnet(255, 255, 255, 0);        // Set your subnet mask
  IPAddress dns(8, 8, 8, 8);                 // Optional: set DNS

  WiFi.config(local_IP, gateway, subnet, dns);
  WiFi.begin(ssid, pass);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  // Setup web server
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/temperature", []() {
    float temperature = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].temperature;
    server.send(200, "text/plain", String(temperature, 1));
  });
  server.on("/humidity", []() {
    float humidity = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].humidity;
    server.send(200, "text/plain", String(humidity, 1));
  });
  server.on("/lightlevel", []() {
    int lightValue = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].lightValue;
    server.send(200, "text/plain", String(lightValue));
  });
  server.on("/dewpoint", []() {
    float temperature = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].temperature;
    float humidity = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].humidity;
    float dewpoint = calculateDewPoint(temperature, humidity);
    server.send(200, "text/plain", String(dewpoint, 1));
  });
  //server.on("/favicon.ico", handleFavicon);
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  static unsigned long lastHistorySave = 0;
  static unsigned long lastSample = 0;

  unsigned long now = millis();

  // Sample sensors as often as you like (e.g., every second)
  static float temperature = NAN;
  static float humidity = NAN;
  static int lightValue = 0;

  if (now - lastSample >= 1000 || lastSample == 0) { // sample every 1s
    temperature = dht.readTemperature();
    humidity = dht.readHumidity();
    lightValue = analogRead(LIGHT_SENSOR_PIN);
    lastSample = now;
  }

  // Store to history every READ_INTERVAL ms
  if (!isnan(temperature) && !isnan(humidity)) {
    if (now - lastHistorySave >= READ_INTERVAL || lastHistorySave == 0) {
      history[historyIndex] = {temperature, humidity, lightValue, now};
      historyIndex = (historyIndex + 1) % HISTORY_SIZE;
      if (historyCount < HISTORY_SIZE) historyCount++;
      lastHistorySave = now;
    }
  }

  server.handleClient();
}

// Serve the main page with current values and a graph
void handleRoot() {
  String html = R"rawliteral(
    <!DOCTYPE html>
    <html>
    <head>
      <title>Weather Station</title>
      <meta http-equiv='refresh' content='300'>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body { font-family: sans-serif; }
        .chart-container { width: 90vw; max-width: 700px; margin: 30px auto; }
      </style>
    </head>
    <body>
      <h1>Weather Station</h1>
  )rawliteral";

  if (historyCount > 0) {
    float temperature = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].temperature;
    float humidity = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].humidity;
    int lightValue = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].lightValue;
    float dewpoint = calculateDewPoint(temperature, humidity);

    html += "<p>Temperature: " + String(temperature, 1) + "&deg;C</p>";
    html += "<p>Humidity: " + String(humidity, 1) + " %</p>";
    html += "<p>Light: " + String(lightValue) + "</p>";
    html += "<p>Dew Point: " + String(dewpoint, 1) + "&deg;C</p>";
  } else {
    html += "<p>No data yet. Please wait...</p>";
  }

  html += R"rawliteral(
      <div class="chart-container"><canvas id="tempChart"></canvas></div>
      <div class="chart-container"><canvas id="humChart"></canvas></div>
      <div class="chart-container"><canvas id="lightChart"></canvas></div>
      <div class="chart-container"><canvas id="dewChart"></canvas></div>
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
          let labels = minsAgoLabels(data.temperatures.length);
          if (labels.length === 0) return;
          new Chart(document.getElementById('tempChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{label: 'Temperature (°C)', data: data.temperatures, borderColor: 'red', fill: false}]
            }
          });
          new Chart(document.getElementById('humChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{label: 'Humidity (%)', data: data.humidities, borderColor: 'blue', fill: false}]
            }
          });
          new Chart(document.getElementById('lightChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{label: 'Light', data: data.lights, borderColor: 'orange', fill: false}]
            }
          });
          new Chart(document.getElementById('dewChart'), {
            type: 'line',
            data: {
              labels: labels,
              datasets: [{label: 'Dew Point (°C)', data: data.dewpoints, borderColor: 'green', fill: false}]
            }
          });
        });
      </script>
    </body>
    </html>
  )rawliteral";

  server.send(200, "text/html", html);
}

// Serve the last hour's data as JSON for the chart
void handleData() {
  String json = "{";
  int start = (historyIndex - historyCount + HISTORY_SIZE) % HISTORY_SIZE;

  json += "\"temperatures\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    json += String(history[idx].temperature, 1);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"humidities\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    json += String(history[idx].humidity, 1);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"lights\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    json += String(history[idx].lightValue);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"dewpoints\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    float dewpoint = calculateDewPoint(history[idx].temperature, history[idx].humidity);
    json += String(dewpoint, 1);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"timestamps\":[";
  unsigned long now = millis();
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    unsigned long minsAgo = (now - history[idx].timestamp) / 60000;
    json += "\"" + String(minsAgo) + "\"";
    if (i < historyCount - 1) json += ",";
  }
  json += "]}";
  server.send(200, "application/json", json);
}