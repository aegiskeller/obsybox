// modify code for deployment on Arduino Uno R4 with WiFi
#include <WiFiS3.h>
#include "arduino_secrets.h" // Make sure this defines ssid and pass
#include <WiFiClient.h>

char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;        // your network password

float rainSensorValue = 0.0;
float safeState = 512; // set desired safeState of the monitor

WiFiServer server(80);

const int NUM_SAMPLES = 30;
int samples[NUM_SAMPLES];
int sampleIndex = 0;
unsigned long lastSampleTime = 0;
float averagedValue = 0;

void setup() {
  pinMode(A0, INPUT_PULLUP);
  Serial.begin(9600);
  Serial.flush();
  Serial.print("notsafe#");

  // Set static IP configuration
  IPAddress local_IP(192, 168, 1, 99);     // Set your desired static IP
  IPAddress gateway(192, 168, 1, 1);        // Set your network gateway
  IPAddress subnet(255, 255, 255, 0);       // Set your subnet mask
  IPAddress dns(8, 8, 8, 8);                // Optional: set DNS

  WiFi.config(local_IP, gateway, subnet, dns);

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
}

void sendRootHtml(WiFiClient& client, bool isSafe) {
  String html = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Rain Sensor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
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
    .a0val {
      position: fixed;
      left: 1em;
      bottom: 1em;
      font-size: 1em;
      color: #bbb;
      font-style: italic;
      opacity: 0.8;
      z-index: 10;
      pointer-events: none;
      user-select: none;
    }
    @media (max-width: 500px) {
      .container { min-width: 0; padding: 1.2em 0.5em; }
      .status { font-size: 2em; padding: 0.5em 0.7em; }
      h1 { font-size: 1.3em; }
      .a0val { font-size: 0.9em; left: 0.5em; bottom: 0.5em; }
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

  // Add averaged A0 value in small italics at bottom left
  char a0buf[32];
  sprintf(a0buf, "A0 avg: %.1f", averagedValue);
  html += String("<div class='a0val'>") + a0buf + "</div>";

  html += "</div></body></html>";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html");
  client.println("Connection: close");
  client.println();
  client.println(html);
}

void loop() {
  // Sample every 100ms
  if (millis() - lastSampleTime >= 100) {
    lastSampleTime = millis();
    samples[sampleIndex] = analogRead(A0);
    sampleIndex = (sampleIndex + 1) % NUM_SAMPLES;

    // Calculate average
    long sum = 0;
    for (int i = 0; i < NUM_SAMPLES; i++) sum += samples[i];
    averagedValue = sum / (float)NUM_SAMPLES;

    //Serial.print("A0 averaged value: ");
    //Serial.println(averagedValue);
  }

  bool isSafe = averagedValue < safeState;

  WiFiClient client = server.available();
  if (client) {
    Serial.println("New client connected");
    String req = "";
    unsigned long timeout = millis() + 1000;
    while (client.connected() && millis() < timeout) {
      if (client.available()) {
        char c = client.read();
        req += c;
        if (req.endsWith("\r\n\r\n")) break;
      }
    }
    Serial.print("Request: ");
    Serial.println(req);

    // Serve root page for GET /
    if (req.indexOf("GET /") >= 0) {
      sendRootHtml(client, isSafe);
    } else {
      client.println("HTTP/1.1 404 Not Found");
      client.println("Content-Type: text/plain");
      client.println("Connection: close");
      client.println();
      client.println("404 Not Found");
    }
    delay(1);
    client.stop();
    Serial.println("Client disconnected");
  }


  // Serial handling (optional)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('#');
    if (cmd == "S") {
      if (isSafe) {
        Serial.print("safe#");
      } else {
        Serial.print("notsafe#");
      }
    }
  }
}