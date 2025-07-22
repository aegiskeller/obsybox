#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h> // Add this for MQTT support
#include <math.h>
#include <Ticker.h>
#include "arduino_secrets.h"
#include <ESP8266mDNS.h> // Add this at the top with your other includes

// MQTT settings
const char* mqtt_server = "192.168.1.49"; 
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/dewheater";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Non-blocking MQTT reconnect variables
unsigned long lastMqttReconnectAttempt = 0;
const unsigned long mqttReconnectInterval = 5000; // 5 seconds between attempts

// Watchdog variables
Ticker watchdogTicker;
const int WATCHDOG_TIMEOUT = 30; // seconds
unsigned long lastWatchdogReset = 0;
bool watchdogEnabled = false;

// Function to reset the device after watchdog timeout
void resetModule() {
  Serial.println("Watchdog timeout - resetting device!");
  ESP.restart();
}

// Feed the watchdog to prevent reset
void feedWatchdog() {
  if (watchdogEnabled) {
    watchdogTicker.detach(); // Stop the current timer
    watchdogTicker.attach(WATCHDOG_TIMEOUT, resetModule); // Start a new timer
  }
}

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

  // Try to initialize sensor, but don't block forever
  if (!aht.begin()) {
    Serial.println("Could not find AHT10/AHT20 sensor! Check wiring.");
    delay(5000); // Pause briefly, then continue anyway
  }

  // Set static IP address and mDNS hostname
  IPAddress local_IP(192, 168, 1, 73);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  //IPAddress dns(8, 8, 8, 8);
  WiFi.config(local_IP, gateway, subnet); //, dns);

  WiFi.begin(SECRET_SSID, SECRET_PASS);
  Serial.print("Connecting to WiFi");
  unsigned long wifiStartTime = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - wifiStartTime > 60000) { // 1 minute timeout
      Serial.println("\nWiFi connection timeout. Rebooting...");
      ESP.restart();
    }
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Set up mDNS responder for dewheater.local
  if (MDNS.begin("dewheater")) {
    Serial.println("mDNS responder started: dewheater.local");
  } else {
    Serial.println("Error setting up mDNS responder!");
  }

  // Setup MQTT
  mqttClient.setServer(mqtt_server, mqtt_port);

  server.begin();
  
  // Enable watchdog timer (will reset after WATCHDOG_TIMEOUT seconds without feedWatchdog calls)
  watchdogTicker.attach(WATCHDOG_TIMEOUT, resetModule);
  watchdogEnabled = true;
  lastWatchdogReset = millis();
  Serial.println("Watchdog timer enabled");
}

void loop() 
{
  feedWatchdog(); // Feed at start of every loop

  static unsigned long lastPrint = 0;
  static unsigned long lastHeartbeat = 0;
  static float dsTemp = NAN;
  static float ahtTemp = NAN;
  static float ahtHumidity = NAN;
  static String heaterMode = "auto";

  unsigned long now = millis();

  // Non-blocking MQTT reconnection
  if (!mqttClient.connected()) {
    if (now - lastMqttReconnectAttempt > mqttReconnectInterval) {
      lastMqttReconnectAttempt = now;
      Serial.print("MQTT disconnected, attempting reconnect... ");
      if (mqttClient.connect("DewHeater_ESP8266")) {
        Serial.println("connected!");
      } else {
        Serial.print("failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" will try again in 5 seconds");
      }
      feedWatchdog(); // Feed after reconnect attempt
    }
  } else {
    mqttClient.loop();
    feedWatchdog(); // Feed after MQTT loop
  }

  // Update sensor values every 10 seconds
  if (now - lastPrint >= 10000) {
    sensors.requestTemperatures();
    float temp = sensors.getTempCByIndex(0);
    unsigned long start = millis();
    while (temp <= -127.0 && millis() - start < 500) {
        yield();
        temp = sensors.getTempCByIndex(0);
        feedWatchdog(); // Feed during long sensor read
    }
    dsTemp = temp;

    sensors_event_t humidityEvent, tempEvent;
    if (aht.getEvent(&humidityEvent, &tempEvent)) {
      ahtTemp = tempEvent.temperature;
      ahtHumidity = humidityEvent.relative_humidity;
    }

    lastPrint = now;

    // Publish to MQTT every 10 seconds (with sensor updates)
    if (mqttClient.connected()) {
      char payload[256];
      float dewPoint = calculateDewPoint(ahtTemp, ahtHumidity);
      int relayState = digitalRead(RELAY_PIN);
      snprintf(payload, sizeof(payload),
        "{\"temperature\":%.2f,\"humidity\":%.2f,\"teltemp\":%.2f,\"dewpoint\":%.2f,\"heater\":\"%s\",\"offset\":%.2f}",
        ahtTemp, ahtHumidity, dsTemp, dewPoint, 
        relayState == HIGH ? "on" : "off", tempOffset);
      mqttClient.publish(mqtt_topic, payload);
      Serial.println("MQTT data published");
      feedWatchdog(); // Feed after MQTT publish
    }
  }

  // Heartbeat message every 5 seconds
  if (now - lastHeartbeat >= 5000) {
    float dewPoint = calculateDewPoint(ahtTemp, ahtHumidity);
    bool heaterIsOn = (heaterMode == "on") || (heaterMode == "auto" && dsTemp < (ahtTemp + tempOffset));
    Serial.print("[HEARTBEAT] Ambient Temp: ");
    Serial.print(ahtTemp, 2);
    Serial.print(" C, Humidity: ");
    Serial.print(ahtHumidity, 2);
    Serial.print(" %, Telescope Temp: ");
    Serial.print(dsTemp, 2);
    Serial.print(" C, Dew Point: ");
    Serial.print(dewPoint, 2);
    Serial.print(" C, Heater: ");
    Serial.print(heaterIsOn ? "ON" : "OFF");
    Serial.print(", Offset: ");
    Serial.println(tempOffset, 2);
    lastHeartbeat = now;
    feedWatchdog(); // Feed after heartbeat
  }

  // Check WiFi connection and reconnect if needed
  static unsigned long lastWifiCheck = 0;
  if (now - lastWifiCheck > 30000) {
    lastWifiCheck = now;
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi connection lost, reconnecting...");
      WiFi.reconnect();
      feedWatchdog(); // Feed after WiFi reconnect
    }
  }

  // Relay logic: always respond to heaterMode
  if (heaterMode == "on") {
    digitalWrite(RELAY_PIN, HIGH);
  } else if (heaterMode == "off") {
    digitalWrite(RELAY_PIN, LOW);
  } else { // "auto"
    float dewPoint = calculateDewPoint(ahtTemp, ahtHumidity);
    if (dsTemp < (dewPoint + tempOffset)) {
      digitalWrite(RELAY_PIN, HIGH);
    } else {
      digitalWrite(RELAY_PIN, LOW);
    }
  }

  // Serve web page with non-blocking approach
  WiFiClient client = server.available();
  if (client) {
    unsigned long clientStartTime = millis();
    while (client.connected() && !client.available() && millis() - clientStartTime < 500) { 
      yield();
      feedWatchdog(); // Feed during client wait
    }
    String req = "";
    clientStartTime = millis();
    while (client.available() && millis() - clientStartTime < 1000) {
      char c = client.read();
      req += c;
      yield();
      feedWatchdog(); // Feed during client read
    }

    // Parse offset from GET request
    int idx = req.indexOf("offset=");
    if (idx != -1) {
      int endIdx = req.indexOf('&', idx);
      String val = (endIdx == -1) ? req.substring(idx + 7) : req.substring(idx + 7, endIdx);
      tempOffset = val.toFloat();
      if (tempOffset < 0) tempOffset = 0;
      if (tempOffset > 20) tempOffset = 20;
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

    // Show heater relay status based on actual RELAY_PIN state
    int relayState = digitalRead(RELAY_PIN);
    client.print("<div class='reading'>Heater Relay: <span class='value' style='color:");
    client.print(relayState == HIGH ? "#0f0" : "#f44");
    client.print(";'>");
    client.print(relayState == HIGH ? "ON" : "OFF");
    client.println("</span></div>");

    client.println("<form method='GET'>");
    client.println("<label for='offset'>Set Temperature Offset (from Dewpoint):</label>");
    client.print("<input type='range' min='0' max='20' step='0.1' name='offset' id='offset' value='");
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
    feedWatchdog(); // Feed after serving client
  }

  feedWatchdog(); // Feed at end of loop for safety
}