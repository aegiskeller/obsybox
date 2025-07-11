#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ESP8266WiFi.h>
#include <math.h>
#include "arduino_secrets.h"

Adafruit_AHTX0 aht;

// DS18B20 setup
#define ONE_WIRE_BUS 4  // Connect DS18B20 data to D2 (GPIO4)
#define RELAY_PIN 16    // Example relay pin (D0/GPIO16), change as needed
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Function to calculate dew point using AHT10 humidity and temperature
float calculateDewPoint(float tempC, float humidity) {
  const float a = 17.62;
  const float b = 243.12;
  float gamma = (a * tempC) / (b + tempC) + log(humidity / 100.0);
  return (b * gamma) / (a - gamma);
}

WiFiServer server(80);
float tempOffset = 2.0; // Default user offset

void setup() 
{
  Serial.begin(9600);
  sensors.begin();
  sensors.setResolution(9); // Fastest conversion
  Wire.begin(2, 14); // SDA = D2, SCL = D14 for your board
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  if (!aht.begin()) 
  {
    Serial.println("Could not find AHT10/AHT20 sensor! Check wiring.");
    while (1) { yield(); }
  }

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
}

void loop() 
{
  static unsigned long lastPrint = 0;
  static float dsTemp = NAN;
  static float ahtTemp = NAN;
  static float ahtHumidity = NAN;
  static String heaterMode = "auto";

  unsigned long now = millis();

  // Update sensor values every 5 seconds
  if (now - lastPrint >= 5000) {
    sensors.requestTemperatures();
    float temp = sensors.getTempCByIndex(0);
    unsigned long start = millis();
    while (temp <= -127.0 && millis() - start < 500) {
        yield();
        temp = sensors.getTempCByIndex(0);
    }
    dsTemp = temp;

    sensors_event_t humidityEvent, tempEvent;
    aht.getEvent(&humidityEvent, &tempEvent);
    ahtTemp = tempEvent.temperature;
    ahtHumidity = humidityEvent.relative_humidity;

    lastPrint = now;
  }

  // Relay logic: always respond to heaterMode
  if (heaterMode == "on") {
    digitalWrite(RELAY_PIN, HIGH);
  } else if (heaterMode == "off") {
    digitalWrite(RELAY_PIN, LOW);
  } else { // auto
    if (dsTemp < (ahtTemp + tempOffset)) {
      digitalWrite(RELAY_PIN, HIGH);
    } else {
      digitalWrite(RELAY_PIN, LOW);
    }
  }

  // Serve web page
  WiFiClient client = server.available();
  if (client) {
    // Wait for request
    while (client.connected() && !client.available()) { delay(1); }
    String req = ""; // <-- Declare req here
    while (client.available()) {
      char c = client.read();
      req += c;
    }

    // Parse offset from GET request
    int idx = req.indexOf("offset=");
    if (idx != -1) {
      int endIdx = req.indexOf('&', idx);
      String val = (endIdx == -1) ? req.substring(idx + 7) : req.substring(idx + 7, endIdx);
      tempOffset = val.toFloat();
      if (tempOffset < -10) tempOffset = -10;
      if (tempOffset > 10) tempOffset = 10;
    }

    // Parse heater mode from GET request
    int idxHeater = req.indexOf("heater=");
    if (idxHeater != -1) {
      int endIdx = req.indexOf('&', idxHeater);
      String val = (endIdx == -1) ? req.substring(idxHeater + 7) : req.substring(idxHeater + 7, endIdx);
      heaterMode = val;
    }

    // Serve minimal dark web page with slider, auto-refresh, and heater control
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/html");
    client.println("Connection: close");
    client.println();
    client.println("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>");
    client.println("<title>Dew Heater Monitor</title>");
    client.println("<meta http-equiv='refresh' content='20'>"); // Auto-refresh every 20 seconds
    client.println("<style>");
    client.println("body { background: #181a20; color: #eee; font-family: 'Segoe UI', Arial, sans-serif; margin:0; padding:0; }");
    client.println(".container { max-width: 420px; margin: 40px auto; background: #23262e; border-radius: 14px; box-shadow: 0 2px 16px #0008; padding: 2em; }");
    client.println("h1 { text-align:center; font-size:1.5em; margin-bottom:1.2em; letter-spacing:1px; }");
    client.println(".reading { font-size:1.15em; margin: 1em 0; }");
    client.println(".value { font-weight:bold; color:#6cf; }");
    client.println("input[type=range] { width:100%; }");
    client.println("</style></head><body>");
    client.println("<div class='container'>");
    client.println("<h1>Dew Heater Sensor Readings</h1>");
    client.print("<div class='reading'>Telescope Temperature: <span class='value'>");
    client.print(dsTemp, 2);
    client.println(" &deg;C</span></div>");
    client.print("<div class='reading'>Ambient Temperature: <span class='value'>");
    client.print(ahtTemp, 2);
    client.println(" &deg;C</span></div>");
    client.print("<div class='reading'>Ambient Humidity: <span class='value'>");
    client.print(ahtHumidity, 2);
    client.println(" %</span></div>");
    float dewPoint = calculateDewPoint(ahtTemp, ahtHumidity);
    client.print("<div class='reading'>Dew Point: <span class='value'>");
    client.print(dewPoint, 2);
    client.println(" &deg;C</span></div>");
    client.print("<div class='reading'>Temperature Offset: <span class='value' id='offsetval'>");
    client.print(tempOffset, 2);
    client.println(" &deg;C</span></div>");
    client.print("<div class='reading'>Heater: <span class='value' style='color:");
    client.print((heaterMode == "on") || (heaterMode == "auto" && dsTemp < (ahtTemp + tempOffset)) ? "#0f0" : "#f44");
    client.print(";'>");
    client.print((heaterMode == "on") || (heaterMode == "auto" && dsTemp < (ahtTemp + tempOffset)) ? "ON" : "OFF");
    client.println("</span></div>");
    client.println("<form method='GET'>");
    client.println("<label for='offset'>Set Temperature Offset (from Dewpoint):</label>");
    client.print("<input type='range' min='-10' max='10' step='0.1' name='offset' id='offset' value='");
    client.print(tempOffset, 2);
    client.println("' oninput='offsetval.innerText=this.value'><br><br>");
    client.println("<label for='heater'>Heater Control:</label>");
    client.println("<select name='heater' id='heater'>");
    client.print("<option value='auto'");
    if (heaterMode == "auto") client.print(" selected");
    client.println(">Auto</option>");
    client.print("<option value='on'");
    if (heaterMode == "on") client.print(" selected");
    client.println(">On</option>");
    client.print("<option value='off'");
    if (heaterMode == "off") client.print(" selected");
    client.println(">Off</option>");
    client.println("</select>");
    client.println("<input type='submit' value='Set' style='margin-top:1em;width:100%;background:#6cf;color:#181a20;border:none;padding:0.5em 0;border-radius:6px;font-size:1em;'>");
    client.println("</form>");
    client.println("</div></body></html>");
    delay(1);
    client.stop();
  }
}