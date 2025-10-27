#include <WiFiS3.h>
#include <ArduinoMqttClient.h>
#include "arduino_secrets.h"

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// MQTT settings
const char* mqtt_broker = "192.168.1.49";  
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/weather";
const unsigned long mqtt_publish_interval = 60000;  // Publish every 60 seconds
const unsigned long mqtt_connect_timeout = 5000;    // Connection timeout in ms
const unsigned long mqtt_retry_interval = 10000;    // Wait between connection attempts
unsigned long lastMqttPublish = 0;
unsigned long lastMqttConnectAttempt = 0;

WiFiServer server(80);
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Sensor configuration
const int SENSOR_PIN = A0;
const int NUM_SAMPLES = 30;  // Number of samples to average
const float RAIN_THRESHOLD = 950.0;  // ADU threshold for rain detection

// Variables for averaging
int samples[NUM_SAMPLES];
int sampleIndex = 0;
float averagedValue = 0;
unsigned long lastSampleTime = 0;

void setup() {
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  Serial.begin(9600);
  Serial.println("Rain Sensor Monitor Starting...");
  Serial.print("notsafe#");  // Initial state
  
  // Set static IP configuration
  IPAddress local_IP(192, 168, 1, 99);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  
  WiFi.config(local_IP, gateway, subnet);
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, pass);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.print("Connected to WiFi. IP: ");
  Serial.println(WiFi.localIP());
  
  // Initial MQTT connection attempt (non-blocking)
  Serial.println("Starting MQTT connection...");
  lastMqttConnectAttempt = millis();
  mqttClient.connect(mqtt_broker, mqtt_port);
  
  server.begin();
  
  // Initialize samples array
  for (int i = 0; i < NUM_SAMPLES; i++) {
    samples[i] = 0;
  }
}

void loop() {
  // Check for S# command first - highest priority
  while (Serial.available() > 0) {
    int inByte = Serial.read();
    if (inByte == 'S') {
      delay(1); // Very short delay to ensure next byte arrives
      if (Serial.available() > 0) {
        inByte = Serial.read();
        if (inByte == '#') {
          // Immediately respond with safety status
          bool isSafe = (averagedValue <= RAIN_THRESHOLD);
          Serial.print(isSafe ? "safe#" : "notsafe#");
          Serial.flush();
        }
      }
    }
  }

  // Sample every 100ms for sensor averaging
  if (millis() - lastSampleTime >= 100) {
    lastSampleTime = millis();
    samples[sampleIndex] = analogRead(SENSOR_PIN);
    sampleIndex = (sampleIndex + 1) % NUM_SAMPLES;
    
    // Calculate average
    long sum = 0;
    for (int i = 0; i < NUM_SAMPLES; i++) {
      sum += samples[i];
    }
    averagedValue = sum / (float)NUM_SAMPLES;
    
    // Publish to MQTT every 10 seconds
    if (millis() - lastMqttPublish >= mqtt_publish_interval) {
      lastMqttPublish = millis();
      
      // Handle MQTT connection state
      if (!mqttClient.connected()) {
        unsigned long currentTime = millis();
        // Only attempt reconnection if enough time has passed since last attempt
        if (currentTime - lastMqttConnectAttempt >= mqtt_retry_interval) {
          Serial.println("MQTT disconnected, attempting reconnection...");
          lastMqttConnectAttempt = currentTime;
          mqttClient.connect(mqtt_broker, mqtt_port);
        }
      } else {
        // Only publish if connected
        // Create JSON payload with rain sensor value
      String payload = "{\"rain_sensor\":" + String(averagedValue, 1) + "}";
      
      // Publish to MQTT
      mqttClient.beginMessage(mqtt_topic);
      mqttClient.print(payload);
      mqttClient.endMessage();
      
      Serial.print("Published to MQTT: ");
      Serial.println(payload);
      }
    }
  }
  
  // Keep MQTT client connected
  mqttClient.poll();
  
  // Check for client connections
  WiFiClient client = server.available();
  if (client) {
    String currentLine = "";
    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        if (c == '\n') {
          if (currentLine.length() == 0) {
            // Send HTTP response
            sendWebPage(client);
            break;
          } else {
            currentLine = "";
          }
        } else if (c != '\r') {
          currentLine += c;
        }
      }
    }
    client.stop();
  }

  // Serial command checking moved to start of loop
}

void sendWebPage(WiFiClient& client) {
  bool isRaining = (averagedValue > RAIN_THRESHOLD);
  
  // Send HTTP headers
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html");
  client.println("Connection: close");
  client.println();
  
  // Send HTML page
  client.println("<!DOCTYPE html>");
  client.println("<html lang='en'>");
  client.println("<head>");
  client.println("<meta charset='UTF-8'>");
  client.println("<title>Rain Sensor Monitor</title>");
  client.println("<meta name='viewport' content='width=device-width, initial-scale=1'>");
  client.println("<meta http-equiv='refresh' content='5'>");  // Refresh every 5 seconds
  client.println("<style>");
  client.println("body {");
  client.println("  background: linear-gradient(135deg, #232526 0%, #414345 100%);");
  client.println("  color: #fff;");
  client.println("  font-family: 'Segoe UI', Arial, sans-serif;");
  client.println("  min-height: 100vh;");
  client.println("  margin: 0;");
  client.println("  display: flex;");
  client.println("  flex-direction: column;");
  client.println("  align-items: center;");
  client.println("  justify-content: center;");
  client.println("}");
  client.println(".container {");
  client.println("  background: rgba(30,34,40,0.95);");
  client.println("  border-radius: 18px;");
  client.println("  box-shadow: 0 4px 32px rgba(0,0,0,0.25);");
  client.println("  padding: 2.5em 3em;");
  client.println("  text-align: center;");
  client.println("}");
  client.println(".status {");
  client.println("  font-size: 2.5em;");
  client.println("  font-weight: bold;");
  client.println("  margin: 0.5em 0;");
  client.println("  padding: 0.5em 1.5em;");
  client.println("  border-radius: 12px;");
  client.println("}");
  client.println(".dry {");
  client.println("  background: #263238;");
  client.println("  color: #00e676;");
  client.println("}");
  client.println(".wet {");
  client.println("  background: #b71c1c;");
  client.println("  color: #ffd600;");
  client.println("}");
  client.println(".value {");
  client.println("  font-size: 1.2em;");
  client.println("  color: #aaa;");
  client.println("  margin-top: 1em;");
  client.println("}");
  client.println("</style>");
  client.println("</head>");
  client.println("<body>");
  client.println("<div class='container'>");
  client.println("<h1>Rain Sensor Monitor</h1>");
  
  // Status display
  client.print("<div class='status ");
  client.print(isRaining ? "wet" : "dry");
  client.print("'>");
  client.print(isRaining ? "RAINING" : "DRY");
  client.println("</div>");
  
  // Sensor value display
  client.print("<div class='value'>Sensor value: ");
  client.print(averagedValue, 1);
  client.println("</div>");
  
  client.println("</div>");
  client.println("</body>");
  client.println("</html>");
}