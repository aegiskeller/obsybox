#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <math.h>

// Pin definitions
#define DHTPIN 2        // DHT11 data pin connected to NodeMCU D4 
#define DHTTYPE DHT11   // DHT 11
#define LIGHT_SENSOR_PIN A0 // Light sensor connected to analog pin A0

#define READ_INTERVAL 10000 // ms
#define HISTORY_DURATION 3600000UL // 1 hour in ms
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
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  static unsigned long lastHistorySave = 0;

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int lightValue = analogRead(LIGHT_SENSOR_PIN);

  unsigned long now = millis();

  if (!isnan(temperature) && !isnan(humidity)) {
    // Store to history every 60 seconds
    if (now - lastHistorySave >= 60000UL || lastHistorySave == 0) {
      history[historyIndex] = {temperature, humidity, lightValue, now};
      historyIndex = (historyIndex + 1) % HISTORY_SIZE;
      if (historyCount < HISTORY_SIZE) historyCount++;
      lastHistorySave = now;
    }
  }

  server.handleClient();
  delay(READ_INTERVAL);
}

// Serve the main page with current values and a graph
void handleRoot() {
  float temperature = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].temperature;
  float humidity = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].humidity;
  int lightValue = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].lightValue;
  float dewpoint = calculateDewPoint(temperature, humidity);

  // Find min/max for scaling
  float tmin = 1000, tmax = -1000, hmin = 1000, hmax = -1000, lmin = 1024, lmax = -1, dmin = 1000, dmax = -1000;
  int start = (historyIndex - historyCount + HISTORY_SIZE) % HISTORY_SIZE;
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    float t = history[idx].temperature;
    float h = history[idx].humidity;
    int l = history[idx].lightValue;
    float d = calculateDewPoint(t, h);
    if (!isnan(t)) { if (t < tmin) tmin = t; if (t > tmax) tmax = t; }
    if (!isnan(h)) { if (h < hmin) hmin = h; if (h > hmax) hmax = h; }
    if (l < lmin) lmin = l; if (l > lmax) lmax = l;
    if (!isnan(d)) { if (d < dmin) dmin = d; if (d > dmax) dmax = d; }
  }
  if (tmax == tmin) tmax = tmin + 1;
  if (hmax == hmin) hmax = hmin + 1;
  if (lmax == lmin) lmax = lmin + 1;
  if (dmax == dmin) dmax = dmin + 1;

  String html = "<!DOCTYPE html><html><head><title>Weather Station</title>"
    "<meta http-equiv='refresh' content='60'>"
    "<style>svg{margin:20px;}</style>"
    "</head><body>"
    "<h1>Weather Station</h1>"
    "<p>Temperature: " + String(temperature) + " &deg;C</p>"
    "<p>Humidity: " + String(humidity) + " %</p>"
    "<p>Light: " + String(lightValue) + "</p>"
    "<p>Dew Point: " + String(dewpoint) + " &deg;C</p>";

  // SVG for Temperature
  html += "<h3>Temperature (&deg;C)</h3><svg width='600' height='200' style='background:#f0f0f0;border:1px solid #ccc'><polyline fill='none' stroke='red' stroke-width='2' points='";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    int x = (historyCount > 1) ? (i * 600) / (historyCount - 1) : 0;
    int y = 180 - (int)(160 * (history[idx].temperature - tmin) / (tmax - tmin));
    html += String(x) + "," + String(y) + " ";
  }
  html += "' /></svg>";

  // SVG for Humidity
  html += "<h3>Humidity (%)</h3><svg width='600' height='200' style='background:#f0f0f0;border:1px solid #ccc'><polyline fill='none' stroke='blue' stroke-width='2' points='";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    int x = (historyCount > 1) ? (i * 600) / (historyCount - 1) : 0;
    int y = 180 - (int)(160 * (history[idx].humidity - hmin) / (hmax - hmin));
    html += String(x) + "," + String(y) + " ";
  }
  html += "' /></svg>";

  // SVG for Light
  html += "<h3>Light Level</h3><svg width='600' height='200' style='background:#f0f0f0;border:1px solid #ccc'><polyline fill='none' stroke='orange' stroke-width='2' points='";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    int x = (historyCount > 1) ? (i * 600) / (historyCount - 1) : 0;
    int y = 180 - (int)(160 * (history[idx].lightValue - lmin) / (lmax - lmin));
    html += String(x) + "," + String(y) + " ";
  }
  html += "' /></svg>";

  // SVG for Dew Point
  html += "<h3>Dew Point (&deg;C)</h3><svg width='600' height='200' style='background:#f0f0f0;border:1px solid #ccc'><polyline fill='none' stroke='green' stroke-width='2' points='";
  for (int i = 0; i < historyCount; i++) {
    int idx = (start + i) % HISTORY_SIZE;
    float d = calculateDewPoint(history[idx].temperature, history[idx].humidity);
    int x = (historyCount > 1) ? (i * 600) / (historyCount - 1) : 0;
    int y = 180 - (int)(160 * (d - dmin) / (dmax - dmin));
    html += String(x) + "," + String(y) + " ";
  }
  html += "' /></svg>";

  html += "</body></html>";
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