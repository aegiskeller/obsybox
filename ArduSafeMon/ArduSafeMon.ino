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

void handleRoot() {
  String html = "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Rain Sensor Monitor</title><meta name='viewport' content='width=device-width, initial-scale=1'><style>body {background: #181a20;font-family: 'Segoe UI', Arial, sans-serif;color: #e0e0e0;text-align: center;padding: 2em;}.container {background: #23262f;border-radius: 12px;box-shadow: 0 2px 12px rgba(0,0,0,0.5);display: inline-block;padding: 2em 3em;margin-top: 2em;}h1 {color: #ffd600;margin-bottom: 0.5em;}.reading {font-size: 2.5em;margin: 0.5em 0;color: #00e676;}.state {font-size: 2em;margin: 0.5em 0;font-weight: bold;padding: 0.3em 1em;border-radius: 8px;display: inline-block;}.safe {background: #263238;color: #00e676;}.notsafe {background: #b71c1c;color: #ffd600;}.footer {margin-top: 2em;color: #888;font-size: 0.9em;}</style><link rel='icon' type='image/png' href='data:image/png;base64,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'>";
  server.send(200, "text/html", html);
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

  server.on("/", handleRoot);
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