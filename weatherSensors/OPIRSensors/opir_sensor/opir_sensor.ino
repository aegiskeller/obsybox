#include <Wire.h>
#include <WiFiNINA.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_AHTX0.h>
#include <ArduinoMqttClient.h>
#include "arduino_secrets.h"

// WiFi credentials
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

// MQTT settings
const char* mqtt_server = SECRET_MQTT_SERVER;
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/opir_sensor";

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Sensor objects
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
Adafruit_AHTX0 aht10;

WiFiServer server(80);

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    mqttClient.setId("OPIR_MKRWiFi");
    // mqttClient.setUsernamePassword("username", "password"); // Uncomment if needed
    if (mqttClient.connect(mqtt_server, mqtt_port)) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.connectError());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("TSL2591, MLX90614 & AHT10 (MKR WiFi)");

  Wire.begin();

  // Static IP configuration (optional, remove if not needed)
  IPAddress local_IP(192, 168, 1, 101);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  IPAddress dns(8, 8, 8, 8);
  WiFi.config(local_IP, dns, gateway, subnet);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  mqttClient.setId("OPIR_MKRWiFi");
  // mqttClient.setUsernamePassword("username", "password"); // Uncomment if needed
  // mqttClient.setServer(mqtt_server, mqtt_port); // <-- REMOVE or COMMENT OUT this line
  reconnectMQTT();

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

  if (isnan(lux)) {
    lux = 0.0;
  }

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
      <style>
        body { background: #181c24; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; }
        h1 { color: #ffd600; }
        .info { background: #232837; color: #b0b8c0; border-radius: 8px; padding: 18px 24px; max-width: 400px; margin: 32px auto; font-size: 1.2em; }
        .label { color: #ffd600; }
      </style>
    </head>
    <body>
      <h1>Sky Condition Sensors</h1>
      <div class='info'>
        <div><span class='label'>Lux:</span> )rawliteral" + String(lux, 2) + R"rawliteral(</div>
        <div><span class='label'>Sky Temp:</span> )rawliteral" + String(objTemp, 2) + R"rawliteral( &deg;C</div>
        <div><span class='label'>Ambient Temp:</span> )rawliteral" + String(ambTemp, 2) + R"rawliteral( &deg;C</div>
        <div><span class='label'>AHT10 Temp:</span> )rawliteral" + String(ahtTemp, 2) + R"rawliteral( &deg;C</div>
        <div><span class='label'>AHT10 Humidity:</span> )rawliteral" + String(ahtHum, 2) + R"rawliteral( %</div>
      </div>
      <div style="text-align:center;margin-top:2em;">
        <small><em>Sensors: TSL2591 (lux), MLX90614 (sky/ambient temperature), AHT10 (temp/humidity)</em></small>
      </div>
    </body>
    </html>
  )rawliteral");
}

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

  unsigned long now = millis();

  // Publish to MQTT every minute
  if (now - lastMqttPublish >= 60000 || lastMqttPublish == 0) {
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
    if (isnan(lux)) {
      lux = 0.0;
    }

    char payload[256];
    snprintf(payload, sizeof(payload),
      "{\"lux\":%.2f,\"sky\":%.2f,\"ambient\":%.2f,\"ir\":%u,\"full\":%u,\"aht_temp\":%.2f,\"aht_hum\":%.2f}",
      lux, objTemp, ambTemp, ir, full, ahtTemp, ahtHum);

    mqttClient.beginMessage(mqtt_topic);
    mqttClient.print(payload);
    mqttClient.endMessage();

    lastMqttPublish = now;
  }
}