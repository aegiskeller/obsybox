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
  String html = "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Rain Sensor Monitor</title><meta name='viewport' content='width=device-width, initial-scale=1'><style>body {background: #f0f4f8;font-family: 'Segoe UI', Arial, sans-serif;color: #222;text-align: center;padding: 2em;}.container {background: #fff;border-radius: 12px;box-shadow: 0 2px 12px rgba(0,0,0,0.08);display: inline-block;padding: 2em 3em;margin-top: 2em;}h1 {color: #1976d2;margin-bottom: 0.5em;}.reading {font-size: 2.5em;margin: 0.5em 0;color: #388e3c;}.state {font-size: 2em;margin: 0.5em 0;font-weight: bold;padding: 0.3em 1em;border-radius: 8px;display: inline-block;}.safe {background: #c8e6c9;color: #256029;}.notsafe {background: #ffcdd2;color: #b71c1c;}.footer {margin-top: 2em;color: #888;font-size: 0.9em;}</style></head><body><div class='container'><h1>Rain Sensor Monitor</h1><div><div>Sensor Value:</div><div id='sensorValue' class='reading'>--</div></div><div><div>Rain Sensor State:</div><div id='sensorState' class='state'>--</div></div></div><div class='footer'>&copy; 2025 Rain Sensor Monitor</div><script>function updateSensor() {fetch('/rainsensorvalue').then(r => r.text()).then(val => {document.getElementById('sensorValue').textContent = val;});fetch('/rainsensorstate').then(r => r.text()).then(state => {const stateDiv = document.getElementById('sensorState');stateDiv.textContent = state;stateDiv.className = 'state ' + (state === 'safe' ? 'safe' : 'notsafe');});}setInterval(updateSensor, 2000);updateSensor();</script></body></html>";
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