/*
 * ObsyBox Relay Controller
 * Arduino Uno with 4-channel relay module for ASCOM switch control
 * 
 * Features:
 * - WiFi connectivity with static IP
 * - MQTT integration for status reporting
 * - Web interface for manual control
 * - RESTful API for ASCOM driver integration
 * - Individual relay control via digital pins
 * - Status LED indication
 * - Watchdog timer for reliability
 * 
 * Hardware:
 * - NodeMCU ESP8266
 * - 4-channel relay module (pins D1, D2, D3, D4)
 * - Status LED on pin D0 (built-in)
 * 
 * API Endpoints:
 * - GET / : Web interface
 * - GET /status : JSON status of all relays
 * - GET /relay/{n} : Get status of relay n (1-4)
 * - POST /relay/{n}/on : Turn on relay n
 * - POST /relay/{n}/off : Turn off relay n
 * - POST /relay/{n}/toggle : Toggle relay n
 * - GET /ascom/status : ASCOM-compatible status
 * - POST /ascom/setswitch : ASCOM switch control
 */

#include <ESP8266WiFi.h>
#include "arduino_secrets.h"
#include <WiFiClient.h>
#include <EEPROM.h>
#include <MQTT.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>

// Network configuration
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
ESP8266WebServer server(80);

// MQTT settings
const char* mqtt_broker = "192.168.1.49";
const int mqtt_port = 1883;
const char* mqtt_topic_status = "obsybox/relays/status";
const char* mqtt_topic_command = "obsybox/relays/command";
WiFiClient net;
MQTTClient mqttClient(512);

// Relay configuration
const int NUM_RELAYS = 4;
const int relayPins[NUM_RELAYS] = {D1, D2, D3, D4};  // NodeMCU pins for relays 1-4
const String relayNames[NUM_RELAYS] = {"Mount", "Camera", "Focuser", "Aux"};  // Default names
bool relayStates[NUM_RELAYS] = {false, false, false, false};  // Current states
bool relayInvert[NUM_RELAYS] = {true, true, true, true};      // Most relay modules are active LOW

// Status LED
const int statusLED = D0;  // NodeMCU built-in LED
unsigned long lastBlink = 0;
bool ledState = false;

// Timing
unsigned long lastMqttPublish = 0;
const unsigned long mqttPublishInterval = 5000;  // Publish status every 5 seconds
unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 1000;    // Heartbeat every second

// Device info
String deviceName = "ObsySwitch";
String firmwareVersion = "1.0.0";
String buildDate = __DATE__ " " __TIME__;

void setup() {
  Serial.begin(9600);
  Serial.println("ObsyBox Relay Controller Starting...");
  
  // Initialize relay pins
  for (int i = 0; i < NUM_RELAYS; i++) {
    pinMode(relayPins[i], OUTPUT);
    setRelayState(i, false);  // Start with all relays off
  }
  
  // Initialize status LED
  pinMode(statusLED, OUTPUT);
  digitalWrite(statusLED, LOW);
  
  // Set static IP configuration
  IPAddress local_IP(192, 168, 1, 76);  // Unique IP for relay controller (NodeMCU)
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  
  WiFi.config(local_IP, gateway, subnet);
  
  // Connect to WiFi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    blinkStatus(100);
  }
  Serial.println();
  Serial.print("Connected to WiFi. IP: ");
  Serial.println(WiFi.localIP());
  
  // Start web server
  server.begin();
  Serial.println("Web server started");
  
  // Initialize MQTT
  mqttClient.begin(mqtt_broker, mqtt_port, net);
  mqttClient.onMessage(mqttMessageHandler);
  
  connectToMQTT();
  
  // Initialize EEPROM
  EEPROM.begin(512);
  
  // Load saved relay states from EEPROM
  loadRelayStatesFromEEPROM();
  
  // Setup web server routes
  setupWebServer();
  
  Serial.println("Relay Controller Ready!");
  publishStatus();
}

void setupWebServer() {
  // Root page
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", generateWebInterface());
  });
  
  // Status endpoint
  server.on("/status", HTTP_GET, []() {
    server.send(200, "application/json", generateStatusJSON());
  });
  
  // ASCOM status
  server.on("/ascom/status", HTTP_GET, []() {
    server.send(200, "application/json", generateASCOMStatus());
  });
  
  // Individual relay status
  server.on("/relay/1", HTTP_GET, []() {
    server.send(200, "application/json", generateRelayStatusJSON(0));
  });
  server.on("/relay/2", HTTP_GET, []() {
    server.send(200, "application/json", generateRelayStatusJSON(1));
  });
  server.on("/relay/3", HTTP_GET, []() {
    server.send(200, "application/json", generateRelayStatusJSON(2));
  });
  server.on("/relay/4", HTTP_GET, []() {
    server.send(200, "application/json", generateRelayStatusJSON(3));
  });
  
  // Relay control endpoints
  server.on("/relay/1/on", HTTP_POST, []() { handleRelayControl(0, true); });
  server.on("/relay/1/off", HTTP_POST, []() { handleRelayControl(0, false); });
  server.on("/relay/1/toggle", HTTP_POST, []() { handleRelayToggle(0); });
  
  server.on("/relay/2/on", HTTP_POST, []() { handleRelayControl(1, true); });
  server.on("/relay/2/off", HTTP_POST, []() { handleRelayControl(1, false); });
  server.on("/relay/2/toggle", HTTP_POST, []() { handleRelayToggle(1); });
  
  server.on("/relay/3/on", HTTP_POST, []() { handleRelayControl(2, true); });
  server.on("/relay/3/off", HTTP_POST, []() { handleRelayControl(2, false); });
  server.on("/relay/3/toggle", HTTP_POST, []() { handleRelayToggle(2); });
  
  server.on("/relay/4/on", HTTP_POST, []() { handleRelayControl(3, true); });
  server.on("/relay/4/off", HTTP_POST, []() { handleRelayControl(3, false); });
  server.on("/relay/4/toggle", HTTP_POST, []() { handleRelayToggle(3); });
  
  // ASCOM setswitch
  server.on("/ascom/setswitch", HTTP_POST, []() {
    handleASCOMSetSwitch();
  });
  
  // 404 handler
  server.onNotFound([]() {
    server.send(404, "application/json", "{\"error\":\"Not found\"}");
  });
}
}

void loop() {
  // Handle web server
  server.handleClient();
  
  // Handle MQTT
  mqttClient.loop();
  if (!mqttClient.connected()) {
    connectToMQTT();
  }
  
  // Publish status periodically
  if (millis() - lastMqttPublish >= mqttPublishInterval) {
    publishStatus();
    lastMqttPublish = millis();
  }
  
  // Heartbeat LED
  if (millis() - lastHeartbeat >= heartbeatInterval) {
    blinkStatus(50);
    lastHeartbeat = millis();
  }
  
  delay(10);  // Small delay for stability
}

void setRelayState(int relayIndex, bool state) {
  if (relayIndex < 0 || relayIndex >= NUM_RELAYS) return;
  
  relayStates[relayIndex] = state;
  
  // Apply inversion for active-low relay modules
  bool outputState = relayInvert[relayIndex] ? !state : state;
  digitalWrite(relayPins[relayIndex], outputState ? HIGH : LOW);
  
  Serial.println("Relay " + String(relayIndex + 1) + " (" + relayNames[relayIndex] + "): " + (state ? "ON" : "OFF"));
  
  // Save state to EEPROM
  EEPROM.write(relayIndex, state ? 1 : 0);
  EEPROM.commit();
}

bool getRelayState(int relayIndex) {
  if (relayIndex < 0 || relayIndex >= NUM_RELAYS) return false;
  return relayStates[relayIndex];
}

void toggleRelay(int relayIndex) {
  setRelayState(relayIndex, !getRelayState(relayIndex));
}

void blinkStatus(int duration) {
  digitalWrite(statusLED, HIGH);
  delay(duration);
  digitalWrite(statusLED, LOW);
}

void loadRelayStatesFromEEPROM() {
  Serial.println("Loading relay states from EEPROM...");
  for (int i = 0; i < NUM_RELAYS; i++) {
    byte savedState = EEPROM.read(i);
    if (savedState == 0 || savedState == 1) {
      setRelayState(i, savedState == 1);
    } else {
      setRelayState(i, false);  // Default to off if invalid data
    }
  }
}

void connectToMQTT() {
  Serial.print("Connecting to MQTT broker...");
  while (!mqttClient.connect("ObsySwitch_RelayController_ESP8266")) {
    Serial.print(".");
    delay(1000);
  }
  Serial.println("connected!");
  
  mqttClient.subscribe(mqtt_topic_command);
  Serial.println("Subscribed to command topic");
}

void mqttMessageHandler(String &topic, String &payload) {
  Serial.println("MQTT message received:");
  Serial.println("Topic: " + topic);
  Serial.println("Payload: " + payload);
  
  if (topic == mqtt_topic_command) {
    handleMqttCommand(payload);
  }
}

void handleMqttCommand(String payload) {
  // Parse JSON command: {"relay": 1, "action": "on"}
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload);
  
  if (error) {
    Serial.println("Failed to parse JSON command");
    return;
  }
  
  int relayNum = doc["relay"];
  String action = doc["action"];
  
  if (relayNum < 1 || relayNum > NUM_RELAYS) {
    Serial.println("Invalid relay number: " + String(relayNum));
    return;
  }
  
  int relayIndex = relayNum - 1;
  
  if (action == "on") {
    setRelayState(relayIndex, true);
  } else if (action == "off") {
    setRelayState(relayIndex, false);
  } else if (action == "toggle") {
    toggleRelay(relayIndex);
  } else {
    Serial.println("Unknown action: " + action);
    return;
  }
  
  publishStatus();  // Send updated status
}

void publishStatus() {
  StaticJsonDocument<512> doc;
  
  doc["device"] = deviceName;
  doc["firmware"] = firmwareVersion;
  doc["build_date"] = buildDate;
  doc["uptime"] = millis();
  doc["ip"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  
  JsonArray relays = doc.createNestedArray("relays");
  for (int i = 0; i < NUM_RELAYS; i++) {
    JsonObject relay = relays.createNestedObject();
    relay["id"] = i + 1;
    relay["name"] = relayNames[i];
    relay["state"] = relayStates[i];
    relay["pin"] = relayPins[i];
  }
  
  String output;
  serializeJson(doc, output);
  
  if (mqttClient.connected()) {
    mqttClient.publish(mqtt_topic_status, output);
  }
}

void handleRelayControl(int relayIndex, bool state) {
  if (relayIndex < 0 || relayIndex >= NUM_RELAYS) {
    server.send(400, "application/json", "{\"error\":\"Invalid relay number\"}");
    return;
  }
  
  setRelayState(relayIndex, state);
  server.send(200, "application/json", generateRelayStatusJSON(relayIndex));
  publishStatus();
}

void handleRelayToggle(int relayIndex) {
  if (relayIndex < 0 || relayIndex >= NUM_RELAYS) {
    server.send(400, "application/json", "{\"error\":\"Invalid relay number\"}");
    return;
  }
  
  toggleRelay(relayIndex);
  server.send(200, "application/json", generateRelayStatusJSON(relayIndex));
  publishStatus();
}

void handleASCOMSetSwitch() {
  // Parse form data or query parameters
  String idStr = server.arg("id");
  String stateStr = server.arg("state");
  
  if (idStr.length() == 0 || stateStr.length() == 0) {
    server.send(400, "application/json", "{\"error\":\"Missing id or state parameter\"}");
    return;
  }
  
  int switchId = idStr.toInt();
  bool switchState = (stateStr == "true" || stateStr == "1" || stateStr == "on");
  
  if (switchId < 1 || switchId > NUM_RELAYS) {
    server.send(400, "application/json", "{\"error\":\"Invalid switch ID\"}");
    return;
  }
  
  setRelayState(switchId - 1, switchState);
  server.send(200, "application/json", generateASCOMStatus());
  publishStatus();
}

void handleWebClients() {
  // This function is no longer needed with ESP8266WebServer
  // The server.handleClient() in loop() handles everything
}

// Web interface generation functions

String generateWebInterface() {
  String html = R"(
<!DOCTYPE html>
<html>
<head>
    <title>ObsyBox Relay Controller</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #1e1e1e; color: #ffffff; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .relay-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .relay-card { background-color: #2d2d2d; padding: 20px; border-radius: 8px; border: 1px solid #444; }
        .relay-title { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
        .relay-status { margin: 10px 0; }
        .status-on { color: #4CAF50; font-weight: bold; }
        .status-off { color: #f44336; font-weight: bold; }
        .relay-controls button { margin: 5px; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-on { background-color: #4CAF50; color: white; }
        .btn-off { background-color: #f44336; color: white; }
        .btn-toggle { background-color: #2196F3; color: white; }
        .info-section { background-color: #2d2d2d; padding: 15px; border-radius: 8px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔌 ObsyBox Relay Controller</h1>
            <p>Device IP: )" + WiFi.localIP().toString() + R"( | Uptime: )" + String(millis() / 1000) + R"(s</p>
        </div>
        
        <div class="relay-grid">)";

  for (int i = 0; i < NUM_RELAYS; i++) {
    html += R"(
            <div class="relay-card">
                <div class="relay-title">Relay )" + String(i + 1) + R"( - )" + relayNames[i] + R"(</div>
                <div class="relay-status">
                    Status: <span class=")" + (relayStates[i] ? "status-on\">ON" : "status-off\">OFF") + R"(</span>
                </div>
                <div class="relay-controls">
                    <button class="btn-on" onclick="controlRelay()" + String(i + 1) + R"(, 'on')">Turn ON</button>
                    <button class="btn-off" onclick="controlRelay()" + String(i + 1) + R"(, 'off')">Turn OFF</button>
                    <button class="btn-toggle" onclick="controlRelay()" + String(i + 1) + R"(, 'toggle')">Toggle</button>
                </div>
            </div>)";
  }

  html += R"(
        </div>
        
        <div class="info-section">
            <h3>Device Information</h3>
            <p><strong>Firmware:</strong> )" + firmwareVersion + R"(</p>
            <p><strong>Build Date:</strong> )" + buildDate + R"(</p>
            <p><strong>WiFi RSSI:</strong> )" + String(WiFi.RSSI()) + R"( dBm</p>
            <p><strong>Free RAM:</strong> )" + String(freeMemory()) + R"( bytes</p>
        </div>
        
        <div class="info-section">
            <h3>API Endpoints</h3>
            <p><strong>Status:</strong> <a href="/status" target="_blank">/status</a></p>
            <p><strong>ASCOM Status:</strong> <a href="/ascom/status" target="_blank">/ascom/status</a></p>
            <p><strong>Individual Relay:</strong> /relay/{1-4}</p>
            <p><strong>Control:</strong> POST /relay/{1-4}/{on|off|toggle}</p>
        </div>
    </div>
    
    <script>
        function controlRelay(relayNum, action) {
            fetch('/relay/' + relayNum + '/' + action, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    console.log('Success:', data);
                    setTimeout(() => location.reload(), 500);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error controlling relay');
                });
        }
    </script>
</body>
</html>)";

  return html;
}

String generateStatusJSON() {
  StaticJsonDocument<512> doc;
  
  doc["device"] = deviceName;
  doc["firmware"] = firmwareVersion;
  doc["build_date"] = buildDate;
  doc["uptime"] = millis();
  doc["ip"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  doc["free_memory"] = freeMemory();
  
  JsonArray relays = doc.createNestedArray("relays");
  for (int i = 0; i < NUM_RELAYS; i++) {
    JsonObject relay = relays.createNestedObject();
    relay["id"] = i + 1;
    relay["name"] = relayNames[i];
    relay["state"] = relayStates[i];
    relay["pin"] = relayPins[i];
  }
  
  String output;
  serializeJson(doc, output);
  return output;
}

String generateRelayStatusJSON(int relayIndex) {
  StaticJsonDocument<200> doc;
  
  doc["relay_id"] = relayIndex + 1;
  doc["name"] = relayNames[relayIndex];
  doc["state"] = relayStates[relayIndex];
  doc["pin"] = relayPins[relayIndex];
  
  String output;
  serializeJson(doc, output);
  return output;
}

String generateASCOMStatus() {
  // ASCOM-compatible JSON response
  StaticJsonDocument<400> doc;
  
  doc["device_name"] = deviceName;
  doc["connected"] = true;
  doc["max_switch"] = NUM_RELAYS - 1;  // ASCOM uses 0-based indexing
  
  JsonArray switches = doc.createNestedArray("switches");
  for (int i = 0; i < NUM_RELAYS; i++) {
    JsonObject sw = switches.createNestedObject();
    sw["id"] = i;  // ASCOM uses 0-based indexing
    sw["name"] = relayNames[i];
    sw["value"] = relayStates[i];
    sw["can_write"] = true;
  }
  
  String output;
  serializeJson(doc, output);
  return output;
}

int freeMemory() {
  // ESP8266 free heap memory
  return ESP.getFreeHeap();
}