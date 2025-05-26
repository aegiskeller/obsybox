#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
// WiFi credentials
#include "arduino_secrets.h"
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)

float rainSensorValue = 0.0;
float safeState = 512; //set desired safeState of the monitor

ESP8266WebServer server(80);

void handleRainSensorValue() {
  rainSensorValue = analogRead(A0);
  server.send(200, "text/plain", String(rainSensorValue));
}

void handleRainSensorState() {
  rainSensorValue = analogRead(A0);
  if (rainSensorValue < safeState) {
    server.send(200, "text/plain", "safe");
  } else {
    server.send(200, "text/plain", "notsafe");
  }
}

void setup() {
  pinMode(A0, INPUT);
  Serial.begin(9600);
  Serial.flush();
  Serial.print("notsafe#");

  WiFi.begin(ssid, pass);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to WiFi. IP: ");
  Serial.println(WiFi.localIP());

  server.on("/rainsensorvalue", handleRainSensorValue);
  server.on("/rainsensorstate", handleRainSensorState);
  server.begin();
}

void loop() {
  server.handleClient();

  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('#');
    if (cmd == "S") {
      rainSensorValue = analogRead(A0);
      if (rainSensorValue < safeState) {
        Serial.print("safe#");
      }
      if (rainSensorValue > safeState) {
        Serial.print("notsafe#");
      }
    }
  }
}