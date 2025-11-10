/*
 * ObsyBox Relay Controller - Ethernet Version (Compact)
 * Arduino Uno with Ethernet Shield for reliable observatory automation
 * 
 * Optimized for Arduino Uno memory constraints:
 * - Simplified web interface
 * - Basic JSON responses (no ArduinoJson library)
 * - Essential functionality only
 * 
 * Hardware:
 * - Arduino Uno R3
 * - Arduino Ethernet Shield (W5100/W5500)
 * - 4-channel relay module (pins 2, 3, 7, 8)
 * 
 * API Endpoints:
 * - GET / : Simple web interface
 * - GET /status : JSON status of all relays
 * - GET /relay/{n} : Get status of relay n (1-4)
 * - POST /relay/{n}/on : Turn on relay n
 * - POST /relay/{n}/off : Turn off relay n
 * - POST /relay/{n}/toggle : Toggle relay n
 */

#include <SPI.h>
#include <Ethernet.h>
#include <EEPROM.h>

// Network configuration
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};
IPAddress ip(192, 168, 1, 77);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

EthernetServer server(80);

// Relay configuration  
const int NUM_RELAYS = 4;
const int relayPins[NUM_RELAYS] = {2, 3, 7, 8};
const char* relayNames[NUM_RELAYS] = {"Mount", "Camera", "Focuser", "Aux"};
bool relayStates[NUM_RELAYS] = {false, false, false, false};
bool relayInvert[NUM_RELAYS] = {true, true, true, true};

// Status LED and timing
const int statusLED = 13;
unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 1000;

// Device info
const char* deviceName = "ObsySwitch-Ethernet";
const char* firmwareVersion = "1.0.0-Compact";

void setup() {
  Serial.begin(9600);
  while (!Serial) ; 
  
  Serial.println(F("ObsyBox Relay Controller - Ethernet (Compact)"));
  Serial.println(F("============================================"));
  
  // Initialize relay pins
  for (int i = 0; i < NUM_RELAYS; i++) {
    pinMode(relayPins[i], OUTPUT);
    setRelayState(i, false);
  }
  
  // Initialize status LED
  pinMode(statusLED, OUTPUT);
  digitalWrite(statusLED, LOW);
  
  // Load saved relay states
  loadRelayStatesFromEEPROM();
  
  // Initialize Ethernet
  Serial.print(F("Initializing Ethernet..."));
  
  if (Ethernet.begin(mac) == 0) {
    Serial.println(F("DHCP failed, using static IP"));
    Ethernet.begin(mac, ip, gateway, gateway, subnet);
  } else {
    Serial.print(F("DHCP assigned: "));
    Serial.println(Ethernet.localIP());
  }
  
  server.begin();
  Serial.print(F("Server started at: "));
  Serial.println(Ethernet.localIP());
  
  // Ready indication
  for (int i = 0; i < 3; i++) {
    digitalWrite(statusLED, HIGH);
    delay(200);
    digitalWrite(statusLED, LOW);
    delay(200);
  }
  
  Serial.println(F("Ready!"));
  printStatus();
}

void loop() {
  // Maintain DHCP lease
  Ethernet.maintain();
  
  // Handle web clients
  EthernetClient client = server.available();
  if (client) {
    handleClient(client);
  }
  
  // Heartbeat LED
  if (millis() - lastHeartbeat >= heartbeatInterval) {
    digitalWrite(statusLED, !digitalRead(statusLED));
    lastHeartbeat = millis();
  }
}

void setRelayState(int relayIndex, bool state) {
  if (relayIndex < 0 || relayIndex >= NUM_RELAYS) return;
  
  relayStates[relayIndex] = state;
  bool outputState = relayInvert[relayIndex] ? !state : state;
  digitalWrite(relayPins[relayIndex], outputState ? HIGH : LOW);
  
  Serial.print(F("Relay "));
  Serial.print(relayIndex + 1);
  Serial.print(F(" ("));
  Serial.print(relayNames[relayIndex]);
  Serial.print(F("): "));
  Serial.println(state ? F("ON") : F("OFF"));
  
  EEPROM.write(relayIndex, state ? 1 : 0);
}

void loadRelayStatesFromEEPROM() {
  Serial.println(F("Loading relay states..."));
  for (int i = 0; i < NUM_RELAYS; i++) {
    byte savedState = EEPROM.read(i);
    if (savedState <= 1) {
      setRelayState(i, savedState == 1);
    } else {
      setRelayState(i, false);
    }
  }
}

void printStatus() {
  Serial.println(F("\n=== Status ==="));
  Serial.print(F("IP: "));
  Serial.println(Ethernet.localIP());
  Serial.print(F("Free RAM: "));
  Serial.println(freeMemory());
  
  for (int i = 0; i < NUM_RELAYS; i++) {
    Serial.print(F("R"));
    Serial.print(i + 1);
    Serial.print(F(": "));
    Serial.println(relayStates[i] ? F("ON") : F("OFF"));
  }
}

void handleClient(EthernetClient& client) {
  Serial.println(F("Client connected"));
  
  String request = "";
  String line = "";
  
  // Read the first line of the request
  while (client.connected() && client.available()) {
    char c = client.read();
    if (c == '\n') {
      if (line.length() == 0) break; // Empty line = end of headers
      if (request.length() == 0) request = line; // First line
      line = "";
    } else if (c != '\r') {
      line += c;
    }
  }
  
  handleRequest(client, request);
  
  delay(1);
  client.stop();
  Serial.println(F("Client disconnected"));
}

void handleRequest(EthernetClient& client, String request) {
  // Parse request
  int firstSpace = request.indexOf(' ');
  int secondSpace = request.indexOf(' ', firstSpace + 1);
  
  if (firstSpace == -1 || secondSpace == -1) return;
  
  String method = request.substring(0, firstSpace);
  String path = request.substring(firstSpace + 1, secondSpace);
  
  Serial.print(F("Request: "));
  Serial.print(method);
  Serial.print(F(" "));
  Serial.println(path);
  
  // Route requests
  if (method == "GET") {
    if (path == "/" || path == "/index.html") {
      sendWebPage(client);
    } else if (path == "/status") {
      sendStatus(client);
    } else if (path.startsWith("/relay/")) {
      int relayNum = path.substring(7).toInt();
      if (relayNum >= 1 && relayNum <= NUM_RELAYS) {
        sendRelayStatus(client, relayNum - 1);
      } else {
        sendError(client, 400, "Invalid relay number");
      }
    } else {
      sendError(client, 404, "Not found");
    }
  } else if (method == "POST") {
    if (path.startsWith("/relay/")) {
      handleRelayControl(client, path);
    } else {
      sendError(client, 404, "Not found");
    }
  }
}

void handleRelayControl(EthernetClient& client, String path) {
  // Parse path like "/relay/1/on"
  int firstSlash = path.indexOf('/', 7); // After "/relay/"
  if (firstSlash == -1) {
    sendError(client, 400, "Invalid path");
    return;
  }
  
  int relayNum = path.substring(7, firstSlash).toInt();
  String action = path.substring(firstSlash + 1);
  
  if (relayNum < 1 || relayNum > NUM_RELAYS) {
    sendError(client, 400, "Invalid relay number");
    return;
  }
  
  int relayIndex = relayNum - 1;
  
  if (action == "on") {
    setRelayState(relayIndex, true);
  } else if (action == "off") {
    setRelayState(relayIndex, false);
  } else if (action == "toggle") {
    setRelayState(relayIndex, !relayStates[relayIndex]);
  } else {
    sendError(client, 400, "Invalid action");
    return;
  }
  
  sendRelayStatus(client, relayIndex);
}

void sendWebPage(EthernetClient& client) {
  client.println(F("HTTP/1.1 200 OK"));
  client.println(F("Content-Type: text/html"));
  client.println(F("Connection: close"));
  client.println();
  
  client.println(F("<!DOCTYPE html><html><head>"));
  client.println(F("<title>ObsyBox Relay Controller</title>"));
  client.println(F("<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"));
  client.println(F("<meta http-equiv=\"refresh\" content=\"30\">"));
  client.println(F("<style>"));
  client.println(F("body{font-family:Arial;margin:20px;background:#1e1e1e;color:#fff}"));
  client.println(F(".container{max-width:600px;margin:0 auto}"));
  client.println(F(".relay{background:#2d2d2d;margin:10px;padding:15px;border-radius:5px}"));
  client.println(F(".status-on{color:#4CAF50;font-weight:bold}"));
  client.println(F(".status-off{color:#f44336;font-weight:bold}"));
  client.println(F("button{margin:5px;padding:8px 12px;border:none;border-radius:3px;cursor:pointer}"));
  client.println(F(".btn-on{background:#4CAF50;color:white}"));
  client.println(F(".btn-off{background:#f44336;color:white}"));
  client.println(F(".btn-toggle{background:#2196F3;color:white}"));
  client.println(F("</style></head><body>"));
  
  client.println(F("<div class=\"container\">"));
  client.println(F("<h1>🔌 ObsyBox Relay Controller</h1>"));
  client.print(F("<p>IP: "));
  client.print(Ethernet.localIP());
  client.print(F(" | Uptime: "));
  client.print(millis() / 1000);
  client.println(F("s</p>"));
  
  // Relay controls
  for (int i = 0; i < NUM_RELAYS; i++) {
    client.println(F("<div class=\"relay\">"));
    client.print(F("<h3>Relay "));
    client.print(i + 1);
    client.print(F(" - "));
    client.print(relayNames[i]);
    client.println(F("</h3>"));
    
    client.print(F("Status: <span class=\""));
    client.print(relayStates[i] ? F("status-on\">ON") : F("status-off\">OFF"));
    client.println(F("</span><br>"));
    
    client.print(F("<button class=\"btn-on\" onclick=\"location.href='/relay/"));
    client.print(i + 1);
    client.println(F("/on'\">Turn ON</button>"));
    
    client.print(F("<button class=\"btn-off\" onclick=\"location.href='/relay/"));
    client.print(i + 1);
    client.println(F("/off'\">Turn OFF</button>"));
    
    client.print(F("<button class=\"btn-toggle\" onclick=\"location.href='/relay/"));
    client.print(i + 1);
    client.println(F("/toggle'\">Toggle</button>"));
    
    client.println(F("</div>"));
  }
  
  client.println(F("<div style=\"margin-top:20px;font-size:12px\">"));
  client.print(F("Firmware: "));
  client.print(firmwareVersion);
  client.print(F(" | Free RAM: "));
  client.print(freeMemory());
  client.println(F(" bytes</div>"));
  
  client.println(F("</div></body></html>"));
}

void sendStatus(EthernetClient& client) {
  client.println(F("HTTP/1.1 200 OK"));
  client.println(F("Content-Type: application/json"));
  client.println(F("Connection: close"));
  client.println();
  
  client.print(F("{\"device\":\""));
  client.print(deviceName);
  client.print(F("\",\"firmware\":\""));
  client.print(firmwareVersion);
  client.print(F("\",\"uptime\":"));
  client.print(millis());
  client.print(F(",\"ip\":\""));
  client.print(Ethernet.localIP());
  client.print(F("\",\"relays\":["));
  
  for (int i = 0; i < NUM_RELAYS; i++) {
    if (i > 0) client.print(F(","));
    client.print(F("{\"id\":"));
    client.print(i + 1);
    client.print(F(",\"name\":\""));
    client.print(relayNames[i]);
    client.print(F("\",\"state\":"));
    client.print(relayStates[i] ? F("true") : F("false"));
    client.print(F(",\"pin\":"));
    client.print(relayPins[i]);
    client.print(F("}"));
  }
  
  client.println(F("]}"));
}

void sendRelayStatus(EthernetClient& client, int relayIndex) {
  client.println(F("HTTP/1.1 200 OK"));
  client.println(F("Content-Type: application/json"));
  client.println(F("Connection: close"));
  client.println();
  
  client.print(F("{\"relay_id\":"));
  client.print(relayIndex + 1);
  client.print(F(",\"name\":\""));
  client.print(relayNames[relayIndex]);
  client.print(F("\",\"state\":"));
  client.print(relayStates[relayIndex] ? F("true") : F("false"));
  client.print(F(",\"pin\":"));
  client.print(relayPins[relayIndex]);
  client.println(F("}"));
}

void sendError(EthernetClient& client, int code, const char* message) {
  client.print(F("HTTP/1.1 "));
  client.print(code);
  client.println(F(" Error"));
  client.println(F("Content-Type: application/json"));
  client.println(F("Connection: close"));
  client.println();
  
  client.print(F("{\"error\":\""));
  client.print(message);
  client.println(F("\"}"));
}

int freeMemory() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}