#include <ESP8266WiFi.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <math.h>

// WiFi credentials
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";

#define ONE_WIRE_BUS 12
#define RELAY_PIN 16

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
Adafruit_BMP085 bmp180;
WiFiServer server(80);

float tempOffset = 2.0; // User-settable offset (X)

void setup() {
  Serial.begin(9600);
  sensors.begin();
  Wire.begin();
  bmp180.begin();

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin();
}

void loop() {
  // Handle web requests
  WiFiClient client = server.available();
  if (client) {
    String req = "";
    unsigned long timeout = millis() + 1000;
    while (client.connected() && millis() < timeout) {
      if (client.available()) {
        char c = client.read();
        req += c;
        if (c == '\n' && req.endsWith("\r\n\r\n")) break;
      }
    }

    // Parse X from GET request
    int idx = req.indexOf("X=");
    if (idx != -1) {
      int endIdx = req.indexOf(' ', idx);
      String val = req.substring(idx + 2, endIdx == -1 ? req.length() : endIdx);
      tempOffset = val.toFloat();
      if (tempOffset < -20) tempOffset = -20;
      if (tempOffset > 20) tempOffset = 20;
    }

    // Sensor readings
    sensors.requestTemperatures();
    float tempC = sensors.getTempCByIndex(0);
    float bmpTemp = bmp180.readTemperature();
    float bmpPressure = bmp180.readPressure() / 100.0;

    // Dew point calculation (assume 100% RH)
    float humidity = 100.0;
    const float a = 17.62, b = 243.12;
    float gamma = (a * bmpTemp) / (b + bmpTemp) + log(humidity / 100.0);
    float dewPoint = (b * gamma) / (a - gamma);

    // Relay logic
    if (tempC < (dewPoint + tempOffset)) {
      digitalWrite(RELAY_PIN, HIGH);
    } else {
      digitalWrite(RELAY_PIN, LOW);
    }

    // Serve web page
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html");
    client.println("Connection: close");
    client.println();
    client.println("<!DOCTYPE html><html><head><meta charset='utf-8'><title>Sensor Readings</title>");
    client.println("<style>body{font-family:sans-serif;background:#222;color:#eee;}input[type=number]{width:4em;}</style></head><body>");
    client.println("<h2>DS18B20 Temperature: " + String(tempC, 2) + " &deg;C</h2>");
    client.println("<h2>BMP180 Temperature: " + String(bmpTemp, 2) + " &deg;C</h2>");
    client.println("<h2>BMP180 Pressure: " + String(bmpPressure, 2) + " hPa</h2>");
    client.println("<h2>Dew Point: " + String(dewPoint, 2) + " &deg;C</h2>");
    client.println("<h2>Relay: <span style='color:" + String((tempC < (dewPoint + tempOffset)) ? "#0f0" : "#f44") + ";'>" + ((tempC < (dewPoint + tempOffset)) ? "ON" : "OFF") + "</span></h2>");
    client.println("<form method='GET'>");
    client.println("Set X (offset): <input type='number' step='0.1' name='X' value='" + String(tempOffset, 2) + "'> &deg;C ");
    client.println("<input type='submit' value='Set'>");
    client.println("</form>");
    client.println("</body></html>");
    delay(1);
    client.stop();
  }
}