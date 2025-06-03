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

  String html = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Weather Station</title>";
  html += "<meta http-equiv='refresh' content='60'>";
  html += "</head><body>";
  html += "<h1>Current Readings</h1>";
  html += "<p>Temperature: " + String(temperature, 1) + " &deg;C</p>";
  html += "<p>Humidity: " + String(humidity, 1) + " %</p>";
  html += "<p>Wind Speed (ADC): " + String(windspeed, 1) + "</p>";

  // --- Temperature & Humidity SVG Plot with Axes, Ticks, and Grid Lines ---
  html += "<h2>Last 30 Minutes (Temperature & Humidity)</h2>";
  html += "<svg width='640' height='220' style='background:#f0f0f0;border:1px solid #ccc'>";
  html += "<g>"; // Group for axes and grid

  // Draw Y grid lines and ticks (5 intervals)
  for (int i = 0; i <= 5; i++) {
    int y = 30 + i * 32; // 30 to 190 over 160px
    html += "<line x1='40' y1='" + String(y) + "' x2='620' y2='" + String(y) + "' stroke='#ccc' stroke-width='1'/>";
    html += "<line x1='37' y1='" + String(y) + "' x2='43' y2='" + String(y) + "' stroke='#888' stroke-width='2'/>";
    // Temperature scale (left)
    float tval = tmax - (tmax - tmin) * (float)i / 5.0;
    html += "<text x='5' y='" + String(y + 5) + "' font-size='12' fill='red'>" + String(tval, 1) + "</text>";
    // Humidity scale (right)
    float hval = hmax - (hmax - hmin) * (float)i / 5.0;
    html += "<text x='625' y='" + String(y + 5) + "' font-size='12' fill='blue' text-anchor='start'>" + String(hval, 1) + "</text>";
  }
  // Draw axes
  html += "<line x1='40' y1='30' x2='40' y2='190' stroke='#888' stroke-width='2'/>";
  html += "<line x1='40' y1='190' x2='620' y2='190' stroke='#888' stroke-width='2'/>";
  html += "</g>";

  // Plot temperature (red)
  html += "<polyline fill='none' stroke='red' stroke-width='2' points='";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(tempHistory[idx])) {
      int x = 40 + i * 19;
      int y = 190 - (int)(160 * (tempHistory[idx] - tmin) / (tmax - tmin));
      html += String(x) + "," + String(y) + " ";
    }
  }
  html += "' />";

  // Plot humidity (blue)
  html += "<polyline fill='none' stroke='blue' stroke-width='2' points='";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(humHistory[idx])) {
      int x = 40 + i * 19;
      int y = 190 - (int)(160 * (humHistory[idx] - hmin) / (hmax - hmin));
      html += String(x) + "," + String(y) + " ";
    }
  }
  html += "' />";
  html += "</svg>";
  html += "<p><span style='color:red'>Red</span>: Temperature (&deg;C), <span style='color:blue'>Blue</span>: Humidity (%)</p>";

  // --- Wind Speed SVG Plot with Axes, Ticks, and Grid Lines ---
  html += "<h2>Last 30 Minutes (Wind Speed)</h2>";
  html += "<svg width='640' height='220' style='background:#f0f0f0;border:1px solid #ccc\">";
  html += "<g>";
  for (int i = 0; i <= 5; i++) {
    int y = 30 + i * 32;
    html += "<line x1='40' y1='" + String(y) + "' x2='620' y2='" + String(y) + "' stroke='#ccc' stroke-width='1'/>";
    html += "<line x1='37' y1='" + String(y) + "' x2='43' y2='" + String(y) + "' stroke='#888' stroke-width='2'/>";
    float aval = amax - (amax - amin) * (float)i / 5.0;
    html += "<text x='5' y='" + String(y + 5) + "' font-size='12' fill='green'>" + String(aval, 1) + "</text>";
  }
  html += "<line x1='40' y1='30' x2='40' y2='190' stroke='#888' stroke-width='2'/>";
  html += "<line x1='40' y1='190' x2='620' y2='190' stroke='#888' stroke-width='2'/>";
  html += "</g>";
  // Plot wind speed (green)
  html += "<polyline fill='none' stroke='green' stroke-width='2' points='";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE; // oldest to newest
    if (!isnan(anemometerHistory[idx])) {
      int x = 40 + i * 19;
      int y = 190 - (int)(160 * (anemometerHistory[idx] - amin) / (amax - amin));
      html += String(x) + "," + String(y) + " ";
    }
  }
  html += "' />";
  html += "</svg>";
  html += "<p><span style='color:green'>Green</span>: Wind Speed (ADC)</p>";

  html += "</body></html>";
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