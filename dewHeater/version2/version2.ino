#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "arduino_secrets.h"
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <math.h>
#include <PubSubClient.h>

#define ONE_WIRE_BUS 12   // Use pin 12 for DS18B20 data
#define RELAY_PIN 7       // Use pin 7 for relay control
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

WiFiServer server(80);
Adafruit_BMP085 bmp;

#define MQTT_SERVER "192.168.1.49"
#define MQTT_PORT 1883
#define MQTT_TOPIC "obsybox/dewheater"

WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastSerialPrint = 0;
float tempOffset = 5.0; // User-settable offset

// Dew point calculation using Magnus formula
float calculateDewPoint(float tempC, float humidity) {
  const float a = 17.62;
  const float b = 243.12;
  float gamma = (a * tempC) / (b + tempC) + log(humidity / 100.0);
  return (b * gamma) / (a - gamma);
}

// Parse offset from HTTP GET request
void parseOffset(String req) {
  int idx = req.indexOf("offset=");
  if (idx != -1) {
    int endIdx = req.indexOf('&', idx);
    String val = (endIdx == -1) ? req.substring(idx + 7) : req.substring(idx + 7, endIdx);
    tempOffset = val.toFloat();
    if (tempOffset < -10) tempOffset = -10;
    if (tempOffset > 10) tempOffset = 10;
  }
}

void publishStatus(float tempC, float bmpTemp, float pressure, bool heaterOn) {
  char payload[256];
  snprintf(payload, sizeof(payload),
    "{\"telescope_temp\":%.2f,\"ambient_temp\":%.2f,\"pressure\":%.2f,\"heater_on\":%s}",
    tempC, bmpTemp, pressure, heaterOn ? "true" : "false");
  mqttClient.publish(MQTT_TOPIC, payload, true);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  sensors.begin();

  Wire.begin();
  if (!bmp.begin()) {
    Serial.println("Couldn't find BMP180/BMP085 sensor! Check wiring.");
  }

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Heater off by default

  WiFi.begin(SECRET_SSID, SECRET_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin();

  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop() {
  bool heaterOn = false; // Track heater state
  // Print sensor values to Serial every second
  if (millis() - lastSerialPrint >= 1000) {
    sensors.requestTemperatures();
    float tempC = sensors.getTempCByIndex(0);
    float bmpTemp = bmp.readTemperature() + tempOffset;
    float pressure = bmp.readPressure() / 100.0; // hPa

    // Heater control logic
    if (tempC < (bmpTemp)) {
      digitalWrite(RELAY_PIN, HIGH); // Turn heater ON
      heaterOn = true;
      Serial.println("Heater ON");
    } else {
      digitalWrite(RELAY_PIN, LOW);  // Turn heater OFF
      heaterOn = false;
      Serial.println("Heater OFF");
    }

    Serial.print("DS18B20 Temp: ");
    if (tempC == DEVICE_DISCONNECTED_C) {
      Serial.println("Sensor not found");
    } else {
      Serial.print(tempC);
      Serial.println(" °C");
    }
    Serial.print("BMP180 Temp: ");
    Serial.print(bmpTemp);
    Serial.print(" °C, Pressure: ");
    Serial.print(pressure);
    Serial.println(" hPa");

    publishStatus(tempC, bmpTemp, pressure, heaterOn);

    lastSerialPrint = millis();
  }

  WiFiClient client = server.available();
  if (client) {
    unsigned long startTime = millis();
    while (!client.available()) {
      delay(1);
      if (millis() - startTime > 1000) { // 1 second timeout
        client.stop();
        return;
      }
      yield(); // Let the ESP8266 background tasks run
    }
    String req = client.readStringUntil('\r');
    client.flush();

    // Parse offset from GET request if present
    parseOffset(req);

    sensors.requestTemperatures();
    float tempC = sensors.getTempCByIndex(0);
    float bmpTemp = bmp.readTemperature() + tempOffset;
    float pressure = bmp.readPressure() / 100.0; // hPa

    // Heater control logic (repeat for web request context)
    if (tempC < (bmpTemp)) {
      digitalWrite(RELAY_PIN, HIGH); // Turn heater ON
      heaterOn = true;
    } else {
      digitalWrite(RELAY_PIN, LOW);  // Turn heater OFF
      heaterOn = false;
    }

    publishStatus(tempC, bmpTemp, pressure, heaterOn);

    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html");
    client.println("Connection: close");
    client.println();
    client.println("<!DOCTYPE HTML>");
    client.println("<html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>");
    client.println("<title>Dew Heater Monitor</title>");
    client.println("<style>");
    client.println("body { background: #181a20; color: #eee; font-family: 'Segoe UI',Arial,sans-serif; margin:0; padding:0; }");
    client.println(".container { max-width: 400px; margin: 40px auto; background: #23262e; border-radius: 12px; box-shadow: 0 2px 16px #0008; padding: 2em; }");
    client.println("h1 { text-align:center; font-size:1.5em; margin-bottom:1em; }");
    client.println(".reading { font-size:1.2em; margin: 1em 0; }");
    client.println("label { display:block; margin:1em 0 0.5em 0; }");
    client.println("input[type=range] { width:100%; }");
    client.println(".value { font-weight:bold; color:#6cf; }");
    client.println("</style>");
    client.println("</head><body>");
    client.println("<div class='container'>");
    client.println("<h1>Dew Heater Monitor</h1>");
    client.println("</span></div>");
    client.print("<div class='reading'>Telescope Temperature: <span class='value'>");
    if (tempC == DEVICE_DISCONNECTED_C) {
      client.print("Sensor not found");
    } else {
      client.print(tempC, 2);
      client.print(" &deg;C");
    }
    client.println("</span></div>");
    client.print("<div class='reading'>Ambient Temperature: <span class='value'>");
    client.print(bmpTemp, 2);
    client.print(" &deg;C</span></div>");
    client.print("<div class='reading'>Pressure: <span class='value'>");
    client.print(pressure, 2);
    client.print(" hPa</span></div>");

    // Heater status display
    client.print("<div class='reading'>Heater Status: <span class='value' style='color:");
    client.print(heaterOn ? "#0f0" : "#f44");
    client.print(";'>");
    client.print(heaterOn ? "ON" : "OFF");
    client.println("</span></div>");

    // Slider for temperature offset
    client.println("<form method='GET'>");
    client.println("<label for='offset'>Temperature Offset (<span id='offsetval'>");
    client.print(tempOffset, 2);
    client.println("</span> &deg;C)</label>");
    client.print("<input type='range' min='-10' max='10' step='0.1' name='offset' id='offset' value='");
    client.print(tempOffset, 2);
    client.println("' oninput='offsetval.innerText=this.value'>");
    client.println("<input type='submit' value='Set' style='margin-top:1em;width:100%;background:#6cf;color:#181a20;border:none;padding:0.5em 0;border-radius:6px;font-size:1em;'>");
    client.println("</form>");

    client.println("</div>");
    client.println("</body></html>");
    delay(1);
    client.stop();
  }

  mqttClient.loop();
}
