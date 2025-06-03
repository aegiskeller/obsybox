#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

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
int historyIndex = 0;
unsigned long lastSampleTime = 0;

// Add these global variables to store the latest averages
float lastAvgTemperature = NAN;
float lastAvgHumidity = NAN;
float lastAvgAnemometer = NAN;

void handleRoot() {
  float temperature = tempHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE];
  float humidity = humHistory[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE];
  float windspeed = lastAvgAnemometer; // Use the latest averaged anemometer value

  String html = "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Weather Station</title></head><body>";
  html += "<h1>Current Readings</h1>";
  html += "<p>Temperature: " + String(temperature, 1) + " &deg;C</p>";
  html += "<p>Humidity: " + String(humidity, 1) + " %</p>";
  html += "<p>Wind Speed (ADC): " + String(windspeed, 1) + "</p>";

  // SVG plot for temperature and humidity
  html += "<h2>Last 30 Minutes</h2>";
  html += "<svg width='600' height='200' style='background:#f0f0f0;border:1px solid #ccc'>";
  float tmin = 1000, tmax = -1000, hmin = 1000, hmax = -1000;
  for (int i = 0; i < HISTORY_SIZE; i++) {
    if (!isnan(tempHistory[i])) {
      if (tempHistory[i] < tmin) tmin = tempHistory[i];
      if (tempHistory[i] > tmax) tmax = tempHistory[i];
    }
    if (!isnan(humHistory[i])) {
      if (humHistory[i] < hmin) hmin = humHistory[i];
      if (humHistory[i] > hmax) hmax = humHistory[i];
    }
  }
  if (tmax == tmin) tmax = tmin + 1;
  if (hmax == hmin) hmax = hmin + 1;

  // Plot temperature (red)
  html += "<polyline fill='none' stroke='red' stroke-width='2' points='";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(tempHistory[idx])) {
      int x = i * 20;
      int y = 180 - (int)(160 * (tempHistory[idx] - tmin) / (tmax - tmin));
      html += String(x) + "," + String(y) + " ";
    }
  }
  html += "' />";
  // Plot humidity (blue)
  html += "<polyline fill='none' stroke='blue' stroke-width='2' points='";
  for (int i = 0; i < HISTORY_SIZE; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    if (!isnan(humHistory[idx])) {
      int x = i * 20;
      int y = 180 - (int)(160 * (humHistory[idx] - hmin) / (hmax - hmin));
      html += String(x) + "," + String(y) + " ";
    }
  }
  html += "' />";
  html += "</svg>";
  html += "<p><span style='color:red'>Red</span>: Temperature (&deg;C), <span style='color:blue'>Blue</span>: Humidity (%)</p>";

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

void setup() {
  Serial.begin(115200);
  dht.begin();

  // Initialize history arrays
  for (int i = 0; i < HISTORY_SIZE; i++) {
    tempHistory[i] = NAN;
    humHistory[i] = NAN;
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