#include <DHT.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>

// Pin definitions
#define DHTPIN 2        // DHT11 data pin connected to NodeMCU D4 
#define DHTTYPE DHT11   // DHT 11
#define LIGHT_SENSOR_PIN A0 // Light sensor connected to analog pin A0

#define READ_INTERVAL 2000 // ms
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
  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  // Read sensors
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();
  int lightValue = analogRead(LIGHT_SENSOR_PIN);

  if (!isnan(temperature) && !isnan(humidity)) {
    history[historyIndex] = {temperature, humidity, lightValue, millis()};
    historyIndex = (historyIndex + 1) % HISTORY_SIZE;
    if (historyCount < HISTORY_SIZE) historyCount++;
  }

  server.handleClient();
  delay(READ_INTERVAL);
}

// Serve the main page with current values and a graph
void handleRoot() {
  float temperature = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].temperature;
  float humidity = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].humidity;
  int lightValue = history[(historyIndex - 1 + HISTORY_SIZE) % HISTORY_SIZE].lightValue;

  String html = "<!DOCTYPE html><html><head><title>Weather Station</title>"
    "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
    "</head><body>"
    "<h1>Weather Station</h1>"
    "<p>Temperature: " + String(temperature) + " &deg;C</p>"
    "<p>Humidity: " + String(humidity) + " %</p>"
    "<p>Light: " + String(lightValue) + "</p>"
    "<canvas id='chart' width='400' height='200'></canvas>"
    "<script>"
    "fetch('/data').then(r=>r.json()).then(data=>{"
    "const ctx=document.getElementById('chart').getContext('2d');"
    "new Chart(ctx,{type:'line',data:{"
    "labels:data.timestamps,"
    "datasets:["
    "{label:'Temp (C)',data:data.temperatures,borderColor:'red',fill:false},"
    "{label:'Humidity (%)',data:data.humidities,borderColor:'blue',fill:false},"
    "{label:'Light',data:data.lights,borderColor:'orange',fill:false}"
    "]},options:{scales:{x:{display:true,title:{display:true,text:'Time (min ago)'}}}}});"
    "});"
    "</script>"
    "</body></html>";
  server.send(200, "text/html", html);
}

// Serve the last hour's data as JSON for the chart
void handleData() {
  String json = "{";
  json += "\"temperatures\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    json += String(history[idx].temperature, 1);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"humidities\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    json += String(history[idx].humidity, 1);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"lights\":[";
  for (int i = 0; i < historyCount; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    json += String(history[idx].lightValue);
    if (i < historyCount - 1) json += ",";
  }
  json += "],\"timestamps\":[";
  unsigned long now = millis();
  for (int i = 0; i < historyCount; i++) {
    int idx = (historyIndex + i) % HISTORY_SIZE;
    // Show time as minutes ago
    unsigned long minsAgo = (now - history[idx].timestamp) / 60000;
    json += "\"" + String(minsAgo) + "\"";
    if (i < historyCount - 1) json += ",";
  }
  json += "]}";
  server.send(200, "application/json", json);
}