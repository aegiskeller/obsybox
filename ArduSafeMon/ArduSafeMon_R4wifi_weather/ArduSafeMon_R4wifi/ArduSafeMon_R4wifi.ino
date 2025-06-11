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

String lastWeatherJson = "";
unsigned long lastWeatherFetch = 0;
const unsigned long weatherFetchInterval = 30000; // 10 minutes in ms

// --- Add these global variables at the top ---
float maxClouds = 100;
float maxWind = 100;
float maxHumidity = 100;

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

// --- Add this function to parse user input from the web form ---
void handleSettingsUpdate(String req) {
  int cloudsIdx = req.indexOf("maxClouds=");
  int windIdx = req.indexOf("maxWind=");
  int humidityIdx = req.indexOf("maxHumidity=");
  if (cloudsIdx >= 0) {
    int end = req.indexOf('&', cloudsIdx);
    String val = req.substring(cloudsIdx + 10, end > 0 ? end : req.length());
    maxClouds = val.toFloat();
  }
  if (windIdx >= 0) {
    int end = req.indexOf('&', windIdx);
    String val = req.substring(windIdx + 8, end > 0 ? end : req.length());
    maxWind = val.toFloat();
  }
  if (humidityIdx >= 0) {
    int end = req.indexOf('&', humidityIdx);
    String val = req.substring(humidityIdx + 12, end > 0 ? end : req.length());
    maxHumidity = val.toFloat();
  }
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
  <meta http-equiv="refresh" content="10">
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
    .weather {
      margin-top: 2em;
      padding: 1em;
      background: #222b;
      border-radius: 12px;
      font-size: 1.1em;
      color: #fff;
      display: inline-block;
      min-width: 220px;
    }
    .weather-title {
      font-weight: bold;
      color: #ffd600;
      margin-bottom: 0.5em;
      font-size: 1.2em;
    }
    .settings-form {
      margin-top: 2em;
      background: #333a;
      padding: 1em 2em;
      border-radius: 12px;
      display: inline-block;
      color: #fff;
    }
    .settings-form label {
      display: inline-block;
      min-width: 120px;
      text-align: right;
      margin-right: 0.5em;
    }
    .settings-form input[type="number"] {
      width: 60px;
      border-radius: 6px;
      border: none;
      padding: 0.2em 0.5em;
      margin-bottom: 0.5em;
      font-size: 1em;
    }
    .settings-form input[type="submit"] {
      margin-top: 0.7em;
      padding: 0.4em 1.2em;
      border-radius: 8px;
      border: none;
      background: #ffd600;
      color: #222;
      font-weight: bold;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.2s;
    }
    .settings-form input[type="submit"]:hover {
      background: #fff176;
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

  // Add averaged A0 value in small italics at bottom left
  char a0buf[32];
  sprintf(a0buf, "A0 avg: %.1f", averagedValue);
  html += String("<div class='a0val'>") + a0buf + "</div>";

  // --- Weather rendering ---
  float cloudsVal = -1, windVal = -1, humidityVal = -1;
  if (lastWeatherJson.length() > 0) {
    // Try to extract simple fields from the JSON (not a full JSON parser)
    String temp = "", humidity = "", desc = "", wind = "", clouds = "";
    int tIdx = lastWeatherJson.indexOf("\"temperature\":");
    if (tIdx > 0) temp = lastWeatherJson.substring(tIdx + 14, lastWeatherJson.indexOf(",", tIdx));
    int hIdx = lastWeatherJson.indexOf("\"humidity\":");
    if (hIdx > 0) {
      humidity = lastWeatherJson.substring(hIdx + 11, lastWeatherJson.indexOf(",", hIdx));
      humidityVal = humidity.toFloat();
    }
    int dIdx = lastWeatherJson.indexOf("\"weather\":");
    if (dIdx > 0) {
      int dq = lastWeatherJson.indexOf("\"", dIdx + 11);
      int dq2 = lastWeatherJson.indexOf("\"", dq + 1);
      int commaAfterDesc = lastWeatherJson.indexOf(",", dIdx);
      if (dq > 0 && dq2 > dq && (commaAfterDesc == -1 || dq2 < commaAfterDesc)) {
        desc = lastWeatherJson.substring(dq + 1, dq2);
      }
    }
    int wIdx = lastWeatherJson.indexOf("\"wind_speed\":");
    if (wIdx > 0) {
      wind = lastWeatherJson.substring(wIdx + 13, lastWeatherJson.indexOf(",", wIdx));
      wind.trim();
      if (wind.endsWith("}")) {
        wind.remove(wind.length() - 1);
        wind.trim();
      }
      windVal = wind.toFloat();
    }
    int cIdx = lastWeatherJson.indexOf("\"clouds\":");
    if (cIdx > 0) {
      clouds = lastWeatherJson.substring(cIdx + 9, lastWeatherJson.indexOf(",", cIdx));
      cloudsVal = clouds.toFloat();
    }

    html += "<div class='weather'>";
    html += "<div class='weather-title'>Current Weather</div>";
    if (temp.length() > 0) html += "Temperature: " + temp + " &deg;C<br>";
    if (humidity.length() > 0) html += "Humidity: " + humidity + " %<br>";
    if (desc.length() > 0) html += "Description: " + desc + "<br>";
    if (wind.length() > 0) html += "Wind Speed: " + wind + " m/s<br>";
    if (clouds.length() > 0) html += "Clouds: " + clouds + " %<br>";

    html += "</div>";
  } else {
    html += "<div class='weather'><em>Weather data unavailable</em></div>";
  }

  // --- Settings form ---
  html += "<form class='settings-form' method='GET'>";
  html += "<div><label for='maxClouds'>Max Clouds (%)</label>";
  html += "<input type='number' id='maxClouds' name='maxClouds' min='0' max='100' value='" + String(maxClouds, 0) + "'></div>";
  html += "<div><label for='maxWind'>Max Wind (m/s)</label>";
  html += "<input type='number' id='maxWind' name='maxWind' min='0' max='100' value='" + String(maxWind, 0) + "'></div>";
  html += "<div><label for='maxHumidity'>Max Humidity (%)</label>";
  html += "<input type='number' id='maxHumidity' name='maxHumidity' min='0' max='100' value='" + String(maxHumidity, 0) + "'></div>";
  html += "<input type='submit' value='Update'>";
  html += "</form>";

  html += "</div></body></html>";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html");
  client.println("Connection: close");
  client.println();
  client.println(html);
}

String getWeatherFromFlask() {
  const char* host = "192.168.1.3"; // Flask server IP
  const int port = 8080;
  const char* url = "/weather";
  WiFiClient client;
  String payload = "";

  if (client.connect(host, port)) {
    client.print(String("GET ") + url + " HTTP/1.1\r\n" +
                 "Host: " + host + "\r\n" +
                 "Connection: close\r\n\r\n");

    // Wait for response
    unsigned long timeout = millis();
    while (client.connected() && millis() - timeout < 3000) {
      while (client.available()) {
        String line = client.readStringUntil('\n');
        // Skip HTTP headers
        if (line == "\r") break;
      }
      // Now read the body
      while (client.available()) {
        payload += (char)client.read();
      }
    }
    client.stop();
  } else {
    Serial.println("Connection to Flask server failed.");
  }
  return payload;
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
  }

  // Fetch weather every 10 minutes
  if (millis() - lastWeatherFetch > weatherFetchInterval || lastWeatherFetch == 0) {
    String weather = getWeatherFromFlask();
    if (weather.length() > 0) {
      lastWeatherJson = weather;
      Serial.println("Weather updated:");
      Serial.println(lastWeatherJson);
    }
    lastWeatherFetch = millis();
  }

  // Parse weather values for safety check
  float cloudsVal = -1, windVal = -1, humidityVal = -1;
  if (lastWeatherJson.length() > 0) {
    int hIdx = lastWeatherJson.indexOf("\"humidity\":");
    if (hIdx > 0) {
      String humidity = lastWeatherJson.substring(hIdx + 11, lastWeatherJson.indexOf(",", hIdx));
      humidityVal = humidity.toFloat();
    }
    int wIdx = lastWeatherJson.indexOf("\"wind_speed\":");
    if (wIdx > 0) {
      String wind = lastWeatherJson.substring(wIdx + 13, lastWeatherJson.indexOf(",", wIdx));
      wind.trim();
      if (wind.endsWith("}")) {
        wind.remove(wind.length() - 1);
        wind.trim();
      }
      windVal = wind.toFloat();
    }
    int cIdx = lastWeatherJson.indexOf("\"clouds\":");
    if (cIdx > 0) {
      String clouds = lastWeatherJson.substring(cIdx + 9, lastWeatherJson.indexOf(",", cIdx));
      cloudsVal = clouds.toFloat();
    }
  }

  // Safety logic: not safe if any weather value exceeds user limits
  bool isSafe = averagedValue < safeState;
  if ((cloudsVal >= 0 && cloudsVal > maxClouds) ||
      (windVal >= 0 && windVal > maxWind) ||
      (humidityVal >= 0 && humidityVal > maxHumidity)) {
    isSafe = false;
  }

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

    // Handle settings update from GET parameters
    if (req.indexOf("GET /?") >= 0) {
      handleSettingsUpdate(req);
    }

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