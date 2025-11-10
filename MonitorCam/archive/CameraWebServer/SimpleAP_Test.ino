#include <WiFi.h>
#include <WebServer.h>

// Access Point Configuration
const char *ap_ssid = "ESP32-CAM-TEST";
const char *ap_password = "12345678";

// Set AP IP configuration
IPAddress ap_local_IP(192, 168, 4, 1);
IPAddress ap_gateway(192, 168, 4, 1);
IPAddress ap_subnet(255, 255, 255, 0);

WebServer server(80);

void handleRoot() {
  String html = "<!DOCTYPE html><html>";
  html += "<head><title>ESP32-CAM Test</title></head>";
  html += "<body>";
  html += "<h1>ESP32-CAM Access Point Test</h1>";
  html += "<p>If you can see this page, the AP and web server are working!</p>";
  html += "<p>Free Heap: " + String(ESP.getFreeHeap()) + " bytes</p>";
  html += "<p>Connected clients: " + String(WiFi.softAPgetStationNum()) + "</p>";
  html += "</body></html>";
  
  server.send(200, "text/html", html);
  Serial.println("Served test page to client");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== ESP32-CAM Simple AP Test ===");
  
  // Configure and start Access Point
  Serial.println("Configuring Access Point...");
  
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(ap_local_IP, ap_gateway, ap_subnet);
  
  bool ap_success = WiFi.softAP(ap_ssid, ap_password);
  
  if (ap_success) {
    Serial.println("Access Point started successfully!");
    Serial.print("SSID: ");
    Serial.println(ap_ssid);
    Serial.print("Password: ");
    Serial.println(ap_password);
    Serial.print("IP: ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("Failed to start Access Point!");
    return;
  }
  
  // Setup web server
  server.on("/", handleRoot);
  server.begin();
  Serial.println("Web server started");
  Serial.println("Connect to WiFi and go to http://192.168.4.1");
  Serial.println("========================");
}

void loop() {
  server.handleClient();
  
  // Status every 15 seconds
  static unsigned long lastStatus = 0;
  if (millis() - lastStatus > 15000) {
    lastStatus = millis();
    Serial.printf("Status: %d clients connected, %d free heap\n", 
                  WiFi.softAPgetStationNum(), ESP.getFreeHeap());
  }
  
  delay(100);
}