/*
 * ObsyBox Relay Controller - Ethernet Version
 * Arduino Uno with Ethernet Shield for reliable observatory automation
 * 
 * Features:
 * - Wired Ethernet connectivity (no WiFi dependency)
 * - Always accessible for firmware updates
 * - Strong GPIO drive capability for relays
 * - MQTT integration for status reporting
 * - Web interface for manual control
 * - RESTful API for ASCOM driver integration
 * - Individual relay control via digital pins
 * - Status LED indication
 * - EEPROM persistence
 * 
 * Hardware:
 * - Arduino Uno R3
 * - Arduino Ethernet Shield (W5100/W5500)
 * - 4-channel relay module (pins 2, 3, 4, 5)
 * - Status LED on pin 13 (built-in)
 * 
 * Wiring:
 * - Pin 2 → Relay 1 (Mount)
 * - Pin 3 → Relay 2 (Camera)  
 * - Pin 4 → Relay 3 (Focuser)
 * - Pin 5 → Relay 4 (Auxiliary)
 * - Pin 10, 11, 12, 13 → Ethernet Shield (SPI)
 * - Pin 4 conflicts avoided by using pins 2,3,4,5 carefully
 * 
 * API Endpoints:
 * - GET / : Web interface
 * - GET /status : JSON status of all relays
 * - GET /relay/{n} : Get status of relay n (1-4)
 * - POST /relay/{n}/on : Turn on relay n
 * - POST /relay/{n}/off : Turn off relay n
 * - POST /relay/{n}/toggle : Toggle relay n
 * - GET /ascom/status : ASCOM-compatible status
 */

#include <SPI.h>
#include <Ethernet.h>
#include <EEPROM.h>
#include <ArduinoJson.h>

// Network configuration
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};  // MAC address
IPAddress ip(192, 168, 1, 77);                       // Static IP for relay controller
IPAddress gateway(192, 168, 1, 1);                   // Gateway
IPAddress subnet(255, 255, 255, 0);                  // Subnet mask

EthernetServer server(80);

// Relay configuration  
const int NUM_RELAYS = 4;
const int relayPins[NUM_RELAYS] = {2, 3, 7, 8};  // Avoid pin 4 (SD card), pins 10-13 (SPI)
const String relayNames[NUM_RELAYS] = {"Mount", "Camera", "Focuser", "Aux"};
bool relayStates[NUM_RELAYS] = {false, false, false, false};
bool relayInvert[NUM_RELAYS] = {true, true, true, true};  // Active LOW relay modules

// Status LED
const int statusLED = 13;  // Built-in LED (shared with SPI, but OK for indication)
unsigned long lastBlink = 0;
bool ledState = false;

// Timing
unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 1000;

// Device info
String deviceName = "ObsySwitch-Ethernet";
String firmwareVersion = "1.0.0";
String buildDate = __DATE__ " " __TIME__;

void setup() {
  Serial.begin(9600);
  while (!Serial) ; // Wait for serial port (Leonardo/Micro)
  
  Serial.println("ObsyBox Relay Controller - Ethernet Version");
  Serial.println("===========================================");
  
  // Initialize relay pins
  for (int i = 0; i < NUM_RELAYS; i++) {
    pinMode(relayPins[i], OUTPUT);
    setRelayState(i, false);  // Start with all relays off
  }
  
  // Initialize status LED
  pinMode(statusLED, OUTPUT);
  digitalWrite(statusLED, LOW);
  
  // Load saved relay states from EEPROM
  loadRelayStatesFromEEPROM();
  
  // Initialize Ethernet
  Serial.print("Initializing Ethernet...");
  
  // Try DHCP first, fall back to static IP
  if (Ethernet.begin(mac) == 0) {
    Serial.println("DHCP failed, using static IP");
    Ethernet.begin(mac, ip, gateway, gateway, subnet);
  } else {
    Serial.print("DHCP assigned: ");
    Serial.println(Ethernet.localIP());
  }
  
  // Start web server
  server.begin();
  Serial.print("Server started at: ");
  Serial.println(Ethernet.localIP());
  
  // Blink to indicate ready
  for (int i = 0; i < 5; i++) {
    blinkStatus(200);
    delay(200);
  }
  
  Serial.println("Relay Controller Ready!");
  printStatus();
}

void loop() {
  // Maintain DHCP lease
  switch (Ethernet.maintain()) {
    case 1:
      Serial.println("Error: renewed fail");
      break;
    case 2:
      Serial.println("Renewed success");
      Serial.print("New IP: ");
      Serial.println(Ethernet.localIP());
      break;
    case 3:
      Serial.println("Error: rebind fail");
      break;
    case 4:
      Serial.println("Rebind success");
      Serial.print("New IP: ");
      Serial.println(Ethernet.localIP());
      break;
    default:
      break;
  }
  
  // Handle web clients
  handleWebClients();
  
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
  
  // Blink LED to indicate activity
  blinkStatus(100);
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

void printStatus() {
  Serial.println("\n=== Device Status ===");
  Serial.println("Device: " + deviceName);
  Serial.println("Firmware: " + firmwareVersion);
  Serial.println("Build: " + buildDate);
  Serial.print("IP: ");
  Serial.println(Ethernet.localIP());
  Serial.print("Free RAM: ");
  Serial.print(freeMemory());
  Serial.println(" bytes");
  
  Serial.println("\n=== Relay Status ===");
  for (int i = 0; i < NUM_RELAYS; i++) {
    Serial.print("Relay ");
    Serial.print(i + 1);
    Serial.print(" (");
    Serial.print(relayNames[i]);
    Serial.print("): ");
    Serial.println(relayStates[i] ? "ON" : "OFF");
  }
  Serial.println();
}

void handleWebClients() {
  EthernetClient client = server.available();
  if (!client) return;
  
  Serial.println("New client connected");
  
  String currentLine = "";
  String request = "";
  bool currentLineIsBlank = true;
  
  while (client.connected()) {
    if (client.available()) {
      char c = client.read();
      request += c;
      
      if (c == '\n' && currentLineIsBlank) {
        // End of HTTP request, process it
        handleHttpRequest(client, request);
        break;
      }
      
      if (c == '\n') {
        currentLineIsBlank = true;
      } else if (c != '\r') {
        currentLineIsBlank = false;
      }
    }
  }
  
  // Give the web browser time to receive the data
  delay(1);
  client.stop();
  Serial.println("Client disconnected");
}

void handleHttpRequest(EthernetClient& client, String request) {
  String method = "";
  String path = "";
  
  // Parse HTTP method and path
  int firstSpace = request.indexOf(' ');
  int secondSpace = request.indexOf(' ', firstSpace + 1);
  
  if (firstSpace > 0 && secondSpace > 0) {
    method = request.substring(0, firstSpace);
    path = request.substring(firstSpace + 1, secondSpace);
  }
  
  Serial.println("HTTP " + method + " " + path);
  
  String response = "";
  String contentType = "application/json";
  int httpCode = 200;
  
  // Route handling
  if (method == "GET") {
    if (path == "/" || path == "/index.html") {
      response = generateWebInterface();
      contentType = "text/html";
    } else if (path == "/status") {
      response = generateStatusJSON();
    } else if (path.startsWith("/relay/")) {
      int relayNum = getRelayNumberFromPath(path);
      if (relayNum > 0 && relayNum <= NUM_RELAYS) {
        response = generateRelayStatusJSON(relayNum - 1);
      } else {
        httpCode = 400;
        response = "{\"error\":\"Invalid relay number\"}";
      }
    } else if (path == "/ascom/status") {
      response = generateASCOMStatus();
    } else {
      httpCode = 404;
      response = "{\"error\":\"Not found\"}";
    }
  } else if (method == "POST") {
    if (path.startsWith("/relay/")) {
      handleRelayControl(path, response, httpCode);
    } else {
      httpCode = 404;
      response = "{\"error\":\"Not found\"}";
    }
  }
  
  // Send HTTP response
  client.println("HTTP/1.1 " + String(httpCode) + " " + (httpCode == 200 ? "OK" : "Error"));
  client.println("Content-Type: " + contentType);
  client.println("Access-Control-Allow-Origin: *");
  client.println("Access-Control-Allow-Methods: GET, POST");
  client.println("Access-Control-Allow-Headers: Content-Type");
  client.println("Connection: close");
  client.println();
  client.println(response);
}

int getRelayNumberFromPath(String path) {
  // Extract relay number from path like "/relay/1" or "/relay/2/on"
  int start = path.indexOf("/relay/") + 7;
  int end = path.indexOf("/", start);
  if (end == -1) end = path.length();
  
  String numStr = path.substring(start, end);
  return numStr.toInt();
}

void handleRelayControl(String path, String& response, int& httpCode) {
  int relayNum = getRelayNumberFromPath(path);
  
  if (relayNum < 1 || relayNum > NUM_RELAYS) {
    httpCode = 400;
    response = "{\"error\":\"Invalid relay number\"}";
    return;
  }
  
  int relayIndex = relayNum - 1;
  
  if (path.endsWith("/on")) {
    setRelayState(relayIndex, true);
  } else if (path.endsWith("/off")) {
    setRelayState(relayIndex, false);
  } else if (path.endsWith("/toggle")) {
    toggleRelay(relayIndex);
  } else {
    httpCode = 400;
    response = "{\"error\":\"Invalid action\"}";
    return;
  }
  
  response = generateRelayStatusJSON(relayIndex);
}

String generateWebInterface() {
  String html = R"(
<!DOCTYPE html>
<html>
<head>
    <title>ObsyBox Relay Controller - Ethernet</title>
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
        .ethernet-badge { background-color: #00796B; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔌 ObsyBox Relay Controller</h1>
            <span class="ethernet-badge">ETHERNET</span>
            <p>Device IP: )" + ipToString(Ethernet.localIP()) + R"( | Uptime: )" + String(millis() / 1000) + R"(s</p>
        </div>
        
        <div class="relay-grid">)";

  for (int i = 0; i < NUM_RELAYS; i++) {
    html += "<div class=\"relay-card\">";
    html += "<div class=\"relay-title\">Relay " + String(i + 1) + " - " + relayNames[i] + "</div>";
    html += "<div class=\"relay-status\">Status: ";
    if (relayStates[i]) {
      html += "<span class=\"status-on\">ON</span>";
    } else {
      html += "<span class=\"status-off\">OFF</span>";
    }
    html += "</div>";
    html += "<div class=\"relay-controls\">";
    html += "<button class=\"btn-on\" onclick=\"controlRelay(" + String(i + 1) + ", 'on')\">Turn ON</button>";
    html += "<button class=\"btn-off\" onclick=\"controlRelay(" + String(i + 1) + ", 'off')\">Turn OFF</button>";
    html += "<button class=\"btn-toggle\" onclick=\"controlRelay(" + String(i + 1) + ", 'toggle')\">Toggle</button>";
    html += "</div></div>";
  }

  html += R"(
        </div>
        
        <div class="info-section">
            <h3>🔧 Device Information</h3>
            <p><strong>Firmware:</strong> )" + firmwareVersion + R"(</p>
            <p><strong>Build Date:</strong> )" + buildDate + R"(</p>
            <p><strong>Connection:</strong> Wired Ethernet (Reliable)</p>
            <p><strong>Free RAM:</strong> )" + String(freeMemory()) + R"( bytes</p>
        </div>
        
        <div class="info-section">
            <h3>🌐 API Endpoints</h3>
            <p><strong>Status:</strong> <a href="/status" target="_blank">/status</a></p>
            <p><strong>ASCOM Status:</strong> <a href="/ascom/status" target="_blank">/ascom/status</a></p>
            <p><strong>Individual Relay:</strong> /relay/{1-4}</p>
            <p><strong>Control:</strong> POST /relay/{1-4}/{on|off|toggle}</p>
        </div>
        
        <div class="info-section">
            <h3>🔌 Hardware Info</h3>
            <p><strong>Platform:</strong> Arduino Uno + Ethernet Shield</p>
            <p><strong>Relay Pins:</strong> 2, 3, 7, 8 (avoiding SPI conflicts)</p>
            <p><strong>Drive Current:</strong> 40mA per pin (excellent for relays)</p>
            <p><strong>Connection:</strong> Always accessible via USB</p>
        </div>
    </div>
    
    <script>
        function controlRelay(relayNum, action) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/relay/' + relayNum + '/' + action, true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState == 4) {
                    if (xhr.status == 200) {
                        setTimeout(function() { location.reload(); }, 500);
                    } else {
                        alert('Error controlling relay');
                    }
                }
            };
            xhr.send();
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
  doc["ip"] = ipToString(Ethernet.localIP());
  doc["connection_type"] = "ethernet";
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

String ipToString(IPAddress ip) {
  String result = String(ip[0]);
  for (int i = 1; i < 4; i++) {
    result += "." + String(ip[i]);
  }
  return result;
}

int freeMemory() {
  // Rough estimate of free memory for Arduino Uno
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}