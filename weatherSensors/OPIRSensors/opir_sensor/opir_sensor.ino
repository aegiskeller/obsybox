#include <Wire.h>
#include <WiFiNINA.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_AHTX0.h>
#include <PubSubClient.h>

#include "arduino_secrets.h"

// WiFi credentials
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

// MQTT settings
const char* mqtt_server = "192.168.1.49";
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/opir_sensor";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// Sensor objects
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
Adafruit_AHTX0 aht10;

// History buffer for 1 hour (60 samples, 1 per minute)
#define HISTORY_SIZE 60
float luxHistory[HISTORY_SIZE];
float objTempHistory[HISTORY_SIZE];
float ambTempHistory[HISTORY_SIZE];
float ahtTempHistory[HISTORY_SIZE];
float ahtHumHistory[HISTORY_SIZE];
int historyIndex = 0;

void addToHistory(float lux, float objTemp, float ambTemp, float ahtTemp, float ahtHum) {
  luxHistory[historyIndex] = lux;
  objTempHistory[historyIndex] = objTemp;
  ambTempHistory[historyIndex] = ambTemp;
  ahtTempHistory[historyIndex] = ahtTemp;
  ahtHumHistory[historyIndex] = ahtHum;
  historyIndex = (historyIndex + 1) % HISTORY_SIZE;
}

WiFiServer server(80);

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect("OPIR_MKRWiFi")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("TSL2591, MLX90614 & AHT10 (MKR WiFi)");

  Wire.begin(); // Default SDA/SCL for MKR boards

  // WiFi connection
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  // MQTT setup
  mqttClient.setServer(mqtt_server, mqtt_port);

  // Sensor init
  if (!tsl.begin()) {
    Serial.println("TSL2591 not found. Check wiring!");
    while (1);
  }
  if (!mlx.begin()) {
    Serial.println("MLX90614 not found. Check wiring!");
    while (1);
  }
  if (!aht10.begin()) {
    Serial.println("AHT10 not found. Check wiring!");
    while (1);
  }
  tsl.setGain(TSL2591_GAIN_MED);
  tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);

  // Initialize history arrays
  for (int i = 0; i < HISTORY_SIZE; i++) {
    luxHistory[i] = NAN;
    objTempHistory[i] = NAN;
    ambTempHistory[i] = NAN;
    ahtTempHistory[i] = NAN;
    ahtHumHistory[i] = NAN;
  }

  server.begin();
  Serial.println("HTTP server started");
}

void serveClient(WiFiClient& client) {
  String req = client.readStringUntil('\r');
  client.flush();

  // Read sensor values
  uint32_t lum = tsl.getFullLuminosity();
  uint16_t ir = lum >> 16;
  uint16_t full = lum & 0xFFFF;
  float lux = tsl.calculateLux(full, ir);
  float objTemp = mlx.readObjectTempC();
  float ambTemp = mlx.readAmbientTempC();
  sensors_event_t humidity, temp;
  aht10.getEvent(&humidity, &temp);
  float ahtTemp = temp.temperature;
  float ahtHum = humidity.relative_humidity;

  // Endpoints
  if (req.indexOf("GET /lux") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(lux, 2);
  } else if (req.indexOf("GET /sky") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(objTemp, 2);
  } else if (req.indexOf("GET /ambient") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(ambTemp, 2);
  } else if (req.indexOf("GET /aht_temp") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(ahtTemp, 2);
  } else if (req.indexOf("GET /aht_hum") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(ahtHum, 2);
  } else if (req.indexOf("GET /data") >= 0) {
    // Prepare JSON with history and current values
    String json = "{";
    json += "\"lux_now\":" + String(luxHistory[(historyIndex + HISTORY_SIZE - 1) % HISTORY_SIZE], 2) + ",";
    json += "\"obj_now\":" + String(objTempHistory[(historyIndex + HISTORY_SIZE - 1) % HISTORY_SIZE], 2) + ",";
    json += "\"amb_now\":" + String(ambTempHistory[(historyIndex + HISTORY_SIZE - 1) % HISTORY_SIZE], 2) + ",";
    json += "\"aht_temp_now\":" + String(ahtTempHistory[(historyIndex + HISTORY_SIZE - 1) % HISTORY_SIZE], 2) + ",";
    json += "\"aht_hum_now\":" + String(ahtHumHistory[(historyIndex + HISTORY_SIZE - 1) % HISTORY_SIZE], 2) + ",";
    json += "\"lux\":[";
    for (int i = 0; i < HISTORY_SIZE; i++) {
      int idx = (historyIndex + i) % HISTORY_SIZE;
      json += isnan(luxHistory[idx]) ? "null" : String(luxHistory[idx], 2);
      if (i < HISTORY_SIZE - 1) json += ",";
    }
    json += "],\"obj\":[";
    for (int i = 0; i < HISTORY_SIZE; i++) {
      int idx = (historyIndex + i) % HISTORY_SIZE;
      json += isnan(objTempHistory[idx]) ? "null" : String(objTempHistory[idx], 2);
      if (i < HISTORY_SIZE - 1) json += ",";
    }
    json += "],\"amb\":[";
    for (int i = 0; i < HISTORY_SIZE; i++) {
      int idx = (historyIndex + i) % HISTORY_SIZE;
      json += isnan(ambTempHistory[idx]) ? "null" : String(ambTempHistory[idx], 2);
      if (i < HISTORY_SIZE - 1) json += ",";
    }
    json += "],\"aht_temp\":[";
    for (int i = 0; i < HISTORY_SIZE; i++) {
      int idx = (historyIndex + i) % HISTORY_SIZE;
      json += isnan(ahtTempHistory[idx]) ? "null" : String(ahtTempHistory[idx], 2);
      if (i < HISTORY_SIZE - 1) json += ",";
    }
    json += "],\"aht_hum\":[";
    for (int i = 0; i < HISTORY_SIZE; i++) {
      int idx = (historyIndex + i) % HISTORY_SIZE;
      json += isnan(ahtHumHistory[idx]) ? "null" : String(ahtHumHistory[idx], 2);
      if (i < HISTORY_SIZE - 1) json += ",";
    }
    json += "]}";
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: application/json");
    client.println("Connection: close");
    client.println();
    client.println(json);
  } else {
    // Serve main HTML page
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html");
    client.println("Connection: close");
    client.println();
    client.println(R"rawliteral(
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
            <span id="lux"></span><br>
            <span id="objTemp"></span><br>
            <span id="ambTemp"></span><br>
            <span id="ahtTemp"></span><br>
            <span id="ahtHum"></span>
          </div>
          <div>Last hour history (1 sample/minute):</div>
        </div>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 24px;">
          <div class="chart-container" style="flex:1 1 320px; min-width:280px; max-width:480px;">
            <canvas id="luxChart"></canvas>
          </div>
          <div class="chart-container" style="flex:1 1 320px; min-width:280px; max-width:480px;">
            <canvas id="tempChart"></canvas>
          </div>
          <div class="chart-container" style="flex:1 1 320px; min-width:280px; max-width:480px;">
            <canvas id="humChart"></canvas>
          </div>
        </div>
        <div style="margin-top:32px; text-align:center;">
          <small><em>Sensors: TSL2591 (lux), MLX90614 (sky/ambient temperature), AHT10 (temp/humidity)</em></small><br>
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
            document.getElementById('objTemp').innerText = "Sky Temp: " + data.obj_now + " °C";
            document.getElementById('ambTemp').innerText = "Ambient Temp: " + data.amb_now + " °C";
            document.getElementById('ahtTemp').innerText = "AHT10 Temp: " + data.aht_temp_now + " °C";
            document.getElementById('ahtHum').innerText = "AHT10 Humidity: " + data.aht_hum_now + " %";
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
            new Chart(document.getElementById('tempChart'), {
              type: 'line',
              data: {
                labels: labels,
                datasets: [
                  {label: 'Sky Temp (°C)', data: data.obj, borderColor: 'red', fill: false},
                  {label: 'Ambient Temp (°C)', data: data.amb, borderColor: 'blue', fill: false},
                  {label: 'AHT10 Temp (°C)', data: data.aht_temp, borderColor: 'green', fill: false}
                ]
              }
            });
            new Chart(document.getElementById('humChart'), {
              type: 'line',
              data: {
                labels: labels,
                datasets: [
                  {label: 'AHT10 Humidity (%)', data: data.aht_hum, borderColor: 'purple', fill: false}
                ]
              }
            });
          });
          setInterval(() => {
            fetchData().then(data => updateValues(data));
          }, 5000);
        </script>
      </body>
      </html>
    )rawliteral");
  }
}

#define SAMPLES_PER_MINUTE 10
float luxSum = 0;
float objTempSum = 0;
float ambTempSum = 0;
float ahtTempSum = 0;
float ahtHumSum = 0;
int sampleCount = 0;
unsigned long lastSampleTime = 0;
unsigned long lastMinuteTime = 0;
unsigned long lastMqttPublish = 0;

void loop() {
  // Handle HTTP requests
  WiFiClient client = server.available();
  if (client) {
    serveClient(client);
    delay(1);
    client.stop();
  }

  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  unsigned long now = millis();

  // Take a sample every 6 seconds (60000 ms / 10)
  if (now - lastSampleTime >= 6000 || lastSampleTime == 0) {
    // Read TSL2591
    uint32_t lum = tsl.getFullLuminosity();
    uint16_t ir = lum >> 16;
    uint16_t full = lum & 0xFFFF;
    float lux = tsl.calculateLux(full, ir);

    // Read MLX90614
    float objTemp = mlx.readObjectTempC();
    float ambTemp = mlx.readAmbientTempC();

    // Read AHT10
    sensors_event_t humidity, temp;
    aht10.getEvent(&humidity, &temp);
    float ahtTemp = temp.temperature;
    float ahtHum = humidity.relative_humidity;

    // Debug output for each sample
    Serial.print("[Sample] Lux: "); Serial.print(lux, 2);
    Serial.print(" | Full: "); Serial.print(full);
    Serial.print(" | IR: "); Serial.print(ir);
    Serial.print(" | Sky Temp: "); Serial.print(objTemp, 2);
    Serial.print(" C | Ambient Temp: "); Serial.print(ambTemp, 2);
    Serial.print(" C | AHT10 Temp: "); Serial.print(ahtTemp, 2);
    Serial.print(" C | AHT10 Humidity: "); Serial.print(ahtHum, 2); Serial.println(" %");

    luxSum += lux;
    objTempSum += objTemp;
    ambTempSum += ambTemp;
    ahtTempSum += ahtTemp;
    ahtHumSum += ahtHum;
    sampleCount++;

    lastSampleTime = now;
  }

  // Publish to MQTT (merged feed)
  if (now - lastMqttPublish >= 60000 || lastMqttPublish == 0) {
    // Read latest values
    uint32_t lum = tsl.getFullLuminosity();
    uint16_t ir = lum >> 16;
    uint16_t full = lum & 0xFFFF;
    float lux = tsl.calculateLux(full, ir);
    float objTemp = mlx.readObjectTempC();
    float ambTemp = mlx.readAmbientTempC();
    sensors_event_t humidity, temp;
    aht10.getEvent(&humidity, &temp);
    float ahtTemp = temp.temperature;
    float ahtHum = humidity.relative_humidity;

    // Publish all sensor values in one JSON object
    char payload[256];
    snprintf(payload, sizeof(payload),
      "{\"lux\":%.2f,\"sky\":%.2f,\"ambient\":%.2f,\"ir\":%u,\"full\":%u,\"aht_temp\":%.2f,\"aht_hum\":%.2f}",
      lux, objTemp, ambTemp, ir, full, ahtTemp, ahtHum);
    mqttClient.publish(mqtt_topic, payload);

    lastMqttPublish = now;
  }

  // Every minute, store the average and reset sums
  if ((now - lastMinuteTime >= 60000 && sampleCount > 0) || lastMinuteTime == 0) {
    float avgLux = luxSum / sampleCount;
    float avgObjTemp = objTempSum / sampleCount;
    float avgAmbTemp = ambTempSum / sampleCount;
    float avgAhtTemp = ahtTempSum / sampleCount;
    float avgAhtHum = ahtHumSum / sampleCount;

    addToHistory(avgLux, avgObjTemp, avgAmbTemp, avgAhtTemp, avgAhtHum);

    // Debug output for each minute
    Serial.print("[Minute AVG] Lux: "); Serial.print(avgLux, 2);
    Serial.print(" | Sky Temp: "); Serial.print(avgObjTemp, 2);
    Serial.print(" C | Ambient Temp: "); Serial.print(avgAmbTemp, 2);
    Serial.print(" C | AHT10 Temp: "); Serial.print(avgAhtTemp, 2);
    Serial.print(" C | AHT10 Humidity: "); Serial.print(avgAhtHum, 2); Serial.println(" %");

    // Reset for next minute
    luxSum = 0;
    objTempSum = 0;
    ambTempSum = 0;
    ahtTempSum = 0;
    ahtHumSum = 0;
    sampleCount = 0;
    lastMinuteTime = now;
  }
}