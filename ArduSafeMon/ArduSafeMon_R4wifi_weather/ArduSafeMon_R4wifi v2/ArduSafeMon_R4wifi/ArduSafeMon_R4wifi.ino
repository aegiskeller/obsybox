// modify code for deployment on Arduino Uno R4 with WiFi
#include <WiFiS3.h>
#include "arduino_secrets.h"
#include <WiFiClient.h>
#include <MQTT.h> // Add ArduinoMqttClient library
#include <WDT.h> // Make sure this is the correct library

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

float rainSensorValue = 0.0;
float safeState = 999;

WiFiServer server(80);

const int NUM_SAMPLES = 30;
int samples[NUM_SAMPLES];
int sampleIndex = 0;
unsigned long lastSampleTime = 0;
float averagedValue = 0;

// MQTT settings
const char* mqtt_broker = "192.168.1.49"; // Set your broker IP
const int mqtt_port = 1883;
const char* mqtt_topic_safety = "obsybox/weathersafety";
WiFiClient net;
MQTTClient mqttClient(512); // Smaller buffer since we only publish

// Add these globals for median safety logic
const int SAFETY_HISTORY_LEN = 60; // 1 minute at 1s intervals
bool safetyHistory[SAFETY_HISTORY_LEN];
int safetyHistoryIdx = 0;
unsigned long lastSafetySample = 0;
unsigned long lastSafetyUpdate = 0;
bool medianSafe = false;

// Add with other global variables
unsigned long lastMqttReconnectAttempt = 0;
const unsigned long mqttReconnectInterval = 5000; // 5 seconds between reconnect attempts
// Add these variables with your other globals
unsigned long mqttFailedTime = 0;
const unsigned long mqttResetTimeout = 180000; // 3 minutes in milliseconds

// Serial connection monitoring variables
unsigned long lastSerialActivity = 0;
unsigned long lastSerialCheck = 0;
bool serialWasConnected = false;

void setup() {
  pinMode(A0, INPUT_PULLUP);
  Serial.begin(9600);
  Serial.flush();
  Serial.print("notsafe#");

  // Set static IP configuration
  IPAddress local_IP(192, 168, 1, 99);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  //IPAddress dns(8, 8, 8, 8);

  WiFi.config(local_IP, gateway, subnet); //, dns);

  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi. IP: ");
  Serial.println(WiFi.localIP());

  server.begin();

  // Initialize samples array
  for (int i = 0; i < NUM_SAMPLES; i++) samples[i] = 0;

  // --- MQTT setup ---
  mqttClient.begin(mqtt_broker, mqtt_port, net);

  Serial.print("Connecting to MQTT broker...");
  while (!mqttClient.connect("ArduSafeMon_R4wifi")) {
    Serial.print(".");
    delay(1000);
  }
  Serial.println("connected!");

  // Initialize the watchdog timer (8 second timeout)
  WDT.begin(8000); // 8000ms = 8s
  Serial.println("Watchdog timer enabled with 8000ms timeout");
  
  // Initialize serial monitoring
  lastSerialActivity = millis();
  serialWasConnected = false;
}

// --- Update sendRootHtml to add the input boxes and form ---
void sendRootHtml(WiFiClient& client, bool isSafe) {
  String html = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Rain Sensor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <style>
    body {
      background: linear-gradient(135deg, #232526 0%, #414345 100%);
      color: #fff;
      font-family: 'Segoe UI', Arial, sans-serif;
      min-height: 100vh;
      margin: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .container {
      background: rgba(30,34,40,0.95);
      border-radius: 18px;
      box-shadow: 0 4px 32px rgba(0,0,0,0.25);
      padding: 2.5em 3em 2em 3em;
      text-align: center;
      min-width: 320px;
    }
    h1 {
      font-size: 2.2em;
      margin-bottom: 0.5em;
      letter-spacing: 0.04em;
      color: #ffd600;
    }
    .status {
      font-size: 3em;
      font-weight: bold;
      margin: 1em 0 0.5em 0;
      padding: 0.5em 1.5em;
      border-radius: 12px;
      display: inline-block;
      transition: background 0.3s, color 0.3s;
      box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    }
    .safe {
      background: #263238;
      color: #00e676;
    }
    .notsafe {
      background: #b71c1c;
      color: #ffd600;
    }
    .timestamp {
      font-size: 1em;
      color: #aaa;
      margin-top: 2em;
      display: block;
      letter-spacing: 0.02em;
    }
    .sensor-info {
      margin-top: 2em;
      padding: 1em;
      background: #222b;
      border-radius: 12px;
      font-size: 1.1em;
      color: #fff;
      display: inline-block;
      min-width: 220px;
    }
    .sensor-title {
      font-weight: bold;
      color: #ffd600;
      margin-bottom: 0.5em;
      font-size: 1.2em;
    }
    .a0val {
      font-size: 1.2em;
      color: #fff;
      margin: 0.5em 0;
    }
    @media (max-width: 500px) {
      .container { min-width: 0; padding: 1.2em 0.5em; }
      .status { font-size: 2em; padding: 0.5em 0.7em; }
      h1 { font-size: 1.3em; }
      .a0val { font-size: 0.9em; left: 0.5em; bottom: 0.5em; }
      .weather { font-size: 1em; min-width: 0; }
      .settings-form { padding: 0.7em 0.5em; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Rain Sensor</h1>
)rawliteral";

  if (isSafe) {
    html += "<div class='status safe'>SAFE</div>";
  } else {
    html += "<div class='status notsafe'>NOT SAFE</div>";
  }

  // Add last updated timestamp (using millis as seconds since power on)
  unsigned long now = millis() / 1000;
  unsigned long hours = now / 3600;
  unsigned long minutes = (now % 3600) / 60;
  unsigned long seconds = now % 60;
  char buf[40];
  sprintf(buf, "%02lu:%02lu:%02lu since power on", hours, minutes, seconds);
  html += String("<div class='timestamp'>Last updated: ") + buf + "</div>";

  // Add sensor info
  html += "<div class='sensor-info'>";
  html += "<div class='sensor-title'>Rain Sensor</div>";
  html += "<div class='a0val'>Current Value: " + String(averagedValue, 1) + "</div>";
  html += "<div class='a0val'>Threshold: " + String(safeState, 1) + "</div>";
  html += "<div style='font-size: 0.9em; color: #bbb; margin-top: 0.5em;'>Safe when value &lt; threshold</div>";
  html += "</div>";

  html += "</div></body></html>";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html");
  client.println("Connection: close");
  client.println();
  client.println(html);
}

void loop() {
  // Reset watchdog at start of loop
  WDT.refresh();

  // --- Serial connection health check ---
  // Check if there's an active USB serial connection
  // The Arduino R4 WiFi reports Serial as "true" when USB is connected
  if (millis() - lastSerialCheck >= 5000) { // Check every 5 seconds
    lastSerialCheck = millis();
    
    // On Arduino R4 WiFi, Serial.dtr() can detect if a host is connected
    // However, this isn't always reliable. Instead, we'll use activity-based detection
    bool currentlyConnected = (bool)Serial;
    
    if (currentlyConnected != serialWasConnected) {
      if (currentlyConnected) {
        Serial.println("Serial connection detected - initializing...");
        Serial.flush();
        delay(100);
        // Send initial state
        if (medianSafe) {
          Serial.print("safe#");
        } else {
          Serial.print("notsafe#");
        }
        serialWasConnected = true;
        lastSerialActivity = millis();
      } else {
        // Connection lost - prepare for reconnection
        serialWasConnected = false;
      }
    }
    
    // Periodically flush the serial buffer to prevent buildup
    if (Serial) {
      Serial.flush();
    }
  }

  // --- Non-blocking MQTT reconnect logic ---
  if (!mqttClient.connected()) {
    unsigned long currentMillis = millis();
    
    // If this is the first disconnect, record the time
    if (mqttFailedTime == 0) {
      mqttFailedTime = currentMillis;
    }
    // Check if we've been disconnected too long
    else if (currentMillis - mqttFailedTime > mqttResetTimeout) {
      Serial.println("MQTT disconnected for more than 3 minutes. Resetting device...");
      delay(500); // Give serial time to send
      
      // Force Arduino reset using watchdog
      WDT.begin(16); // Set shortest timeout (16ms)
      while(1); // Wait for watchdog to reset
      
      // Alternative reset method for Arduino
      // asm volatile ("jmp 0"); // Software reset
    }
    
    // Try reconnecting every 5 seconds
    if (currentMillis - lastMqttReconnectAttempt > mqttReconnectInterval) {
      lastMqttReconnectAttempt = currentMillis;
      Serial.print("MQTT disconnected, attempting reconnect... ");
      if (mqttClient.connect("ArduSafeMon_R4wifi")) {
        Serial.println("connected!");
        mqttFailedTime = 0; // Reset the failure timer on successful connection
        mqttClient.subscribe("obsybox/weathersafety"); // re-subscribe after reconnect
      } else {
        Serial.print("failed, rc=");
        Serial.print(mqttClient.lastError());
        Serial.println(" will try again in 5 seconds");
      }
    }
  } else {
    // If connected, make sure failure timer is reset
    mqttFailedTime = 0;
  }

  mqttClient.loop();
  
  // Sample every 100ms for sensor averaging
  if (millis() - lastSampleTime >= 100) {
    lastSampleTime = millis();
    samples[sampleIndex] = analogRead(A0);
    sampleIndex = (sampleIndex + 1) % NUM_SAMPLES;

    // Calculate average
    long sum = 0;
    for (int i = 0; i < NUM_SAMPLES; i++) sum += samples[i];
    averagedValue = sum / (float)NUM_SAMPLES;
    WDT.refresh(); // Changed from WDT.reset()
  }

  // --- Poll safety state every second and store in history ---
  if (millis() - lastSafetySample >= 1000 || lastSafetySample == 0) {
    lastSafetySample = millis();

    bool isSafe = averagedValue < safeState;
    
    safetyHistory[safetyHistoryIdx] = isSafe;
    safetyHistoryIdx = (safetyHistoryIdx + 1) % SAFETY_HISTORY_LEN;
  }

  // --- Every minute, update the median safety state ---
  if (millis() - lastSafetyUpdate >= 60000 || lastSafetyUpdate == 0) {
    lastSafetyUpdate = millis();

    // Copy history to a temp array and sort to find median
    bool temp[SAFETY_HISTORY_LEN];
    memcpy(temp, safetyHistory, SAFETY_HISTORY_LEN);
    // Count number of true (safe) states
    int safeCount = 0;
    for (int i = 0; i < SAFETY_HISTORY_LEN; i++) {
      if (temp[i]) safeCount++;
    }
    // Median: more than half are safe
    medianSafe = (safeCount > SAFETY_HISTORY_LEN / 2);
    
    Serial.print("Safety history: Safe count = ");
    Serial.print(safeCount);
    Serial.print(" out of ");
    Serial.print(SAFETY_HISTORY_LEN);
    Serial.print(" samples. Median safe = ");
    Serial.println(medianSafe ? "true" : "false");

    // --- Publish safety status to MQTT ---
    String reason = medianSafe ? "Rain sensor safe (median)" : "Rain detected (median)";
    String payload = "{\"safe\":";
    payload += medianSafe ? "true" : "false";
    payload += ",\"reason\":\"" + reason + "\"}";
    mqttClient.publish(mqtt_topic_safety, payload);
  }

  // Reset watchdog before web server handling
  WDT.refresh();  // Changed from WDT.reset()
  
  // --- Web server handling ---
  WiFiClient client = server.available();
  if (client) {
    //Serial.println("New client connected");
    String req = "";
    unsigned long timeout = millis() + 1000;
    while (client.connected() && millis() < timeout) {
      if (client.available()) {
        char c = client.read();
        req += c;
        if (req.endsWith("\r\n\r\n")) break;
      }
    }

    // Serve root page for GET /
    if (req.indexOf("GET /") >= 0) {
      sendRootHtml(client, medianSafe);
    } else {
      client.println("HTTP/1.1 404 Not Found");
      client.println("Content-Type: text/html");
      client.println("Connection: close");
      client.println();
      client.println(
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta charset='UTF-8'>"
        "<meta http-equiv='refresh' content='5'>"
        "<title>404 Not Found</title>"
        "<style>"
        "body { background: linear-gradient(135deg, #232526 0%, #414345 100%); color: #fff; font-family: 'Segoe UI', Arial, sans-serif; min-height: 100vh; margin: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }"
        ".container { background: rgba(30,34,40,0.95); border-radius: 18px; box-shadow: 0 4px 32px rgba(0,0,0,0.25); padding: 2.5em 3em 2em 3em; text-align: center; min-width: 320px; }"
        "h2 { color: #ffd600; font-size: 2.2em; margin-bottom: 0.5em; }"
        "p { color: #fff; font-size: 1.2em; }"
        ".refresh { color: #bbb; font-size: 1em; margin-top: 2em; }"
        "@media (max-width: 500px) { .container { min-width: 0; padding: 1.2em 0.5em; } h2 { font-size: 1.3em; } }"
        "</style>"
        "</head><body>"
        "<div class='container'>"
        "<h2>404 Not Found</h2>"
        "<p>The page you requested was not found.</p>"
        "<div class='refresh'>Page will refresh in 5 seconds.</div>"
        "</div></body></html>"
      );
    }
    delay(1);
    client.stop();
    //Serial.println("Client disconnected");
  }
  
  // Reset watchdog at end of loop for safety
  WDT.refresh();  

  // Check for "S#" command via serial and report safety state
  if (Serial.available()) {
    lastSerialActivity = millis(); // Track serial activity
    String cmd = Serial.readStringUntil('#');
    
    if (cmd == "S") {
      // Send response immediately
      if (medianSafe) {
        Serial.print("safe#");
      } else {
        Serial.print("notsafe#");
      }
      Serial.flush(); // Ensure data is sent immediately
      
      // Print detailed reason after the standard response
      Serial.println("\nSafety Status Details:");
      Serial.print("Rain sensor value: ");
      Serial.print(averagedValue);
      Serial.print(" (threshold: ");
      Serial.print(safeState);
      Serial.println(")");
      
      Serial.print("Safety history: ");
      int safeCount = 0;
      for (int i = 0; i < SAFETY_HISTORY_LEN; i++) {
        if (safetyHistory[i]) safeCount++;
      }
      Serial.print(safeCount);
      Serial.print(" safe readings out of ");
      Serial.print(SAFETY_HISTORY_LEN);
      Serial.println(" samples");
      Serial.flush(); // Flush after all output
    }
    
    // Clear any remaining bytes in the serial buffer
    while (Serial.available() > 0) {
      Serial.read();
    }
  }
}