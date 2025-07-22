#include <WiFiS3.h>         // For Arduino UNO R4 WiFi
#include "arduino_secrets.h" // Contains SECRET_SSID and SECRET_PASS

WiFiServer server(80);

String safetyStatus = "SAFE"; // Change as needed for your test

IPAddress local_IP(192, 168, 1, 99); // Change to match your network
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.print("Connecting to WiFi SSID: ");
  Serial.println(SECRET_SSID);

  WiFi.config(local_IP, gateway, subnet);
  WiFi.begin(SECRET_SSID, SECRET_PASS);

  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Connected! IP address: ");
    Serial.println(WiFi.localIP());
    server.begin();
  } else {
    Serial.println("Failed to connect to WiFi.");
  }

  Serial.print("WiFi firmware version: ");
  Serial.println(WiFi.firmwareVersion());
//  Serial.print("Board MAC: ");
//  Serial.println(WiFi.macAddress());
  Serial.print("WiFi status: ");
  Serial.println(WiFi.status());
  Serial.print("Local IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  WiFiClient client = server.available();
  if (client) {
    // Wait until client sends data
    while (client.connected() && !client.available()) {
      delay(1);
    }
    // Read the request (not used here)
    while (client.available()) client.read();

    // Send a simple HTML page with safety status
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html");
    client.println("Connection: close");
    client.println();
    client.println("<!DOCTYPE html><html><head><title>Safety Status</title></head><body>");
    client.print("<h1>Safety Status: <span style='color:");
    client.print(safetyStatus == "SAFE" ? "green" : "red");
    client.print(";'>");
    client.print(safetyStatus);
    client.println("</span></h1>");
    client.println("</body></html>");
    delay(1);
    client.stop();
  }
}