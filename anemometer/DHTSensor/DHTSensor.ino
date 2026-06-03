/*
  DHT22 temperature & humidity -> MQTT publisher
  Target board: SparkFun ESP8266 Thing Dev

  Hardware:
    DHT22 data pin -> GPIO4 (change DHT_PIN below if wired differently)
    DHT22 VCC      -> 3.3 V
    DHT22 GND      -> GND
    10k pull-up resistor between data pin and VCC is recommended.

  Publishes JSON to obsybox/anemometer every 10 seconds:
    {"temp":21.4,"rh":58.3}

  Libraries required (install via Arduino Library Manager):
    - "DHT sensor library" by Adafruit  (+ Adafruit Unified Sensor)
    - "PubSubClient" by Nick O'Leary

  WiFi credentials are stored in arduino_secrets.h:
    #define SECRET_SSID "your-ssid"
    #define SECRET_PASS "your-password"
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Ticker.h>
#include <DHT.h>
#include "arduino_secrets.h"

// --- Pin / sensor config ------------------------------------------------
#define DHT_PIN  4        // GPIO4 on SparkFun Thing Dev
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);

// --- Network / MQTT settings --------------------------------------------
const char*  MQTT_SERVER = "192.168.1.49";
const int    MQTT_PORT   = 1883;
const char*  MQTT_TOPIC  = "obsybox/anemometer";
const char*  MQTT_CLIENT = "DHTSensor_ThingDev";

// Static IP - adjust to suit your network
IPAddress staticIP(192, 168, 1, 74);   // change if needed
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// --- Watchdog -----------------------------------------------------------
Ticker watchdog;
void watchdogReset() { Serial.println("Watchdog timeout - restarting"); ESP.restart(); }
void feedWatchdog()  { watchdog.detach(); watchdog.once(30, watchdogReset); }

// --- Timing -------------------------------------------------------------
const unsigned long PUBLISH_INTERVAL_MS = 10000UL;  // 10 seconds
unsigned long lastPublish     = 0;
unsigned long lastMqttAttempt = 0;

// --- Setup --------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  Serial.println("\nDHT22 MQTT publisher starting");

  dht.begin();
  delay(2000);  // DHT22 needs time to stabilise on power-up

  // WiFi
  WiFi.mode(WIFI_STA);
  WiFi.config(staticIP, gateway, subnet);
  WiFi.begin(SECRET_SSID, SECRET_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print("."); yield();
  }
  Serial.print("\nConnected, IP: "); Serial.println(WiFi.localIP());

  // MQTT
  mqttClient.setServer(MQTT_SERVER, MQTT_PORT);

  // Watchdog
  feedWatchdog();
}

// --- Main loop ----------------------------------------------------------
void loop() {
  feedWatchdog();

  // Non-blocking MQTT reconnect
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    if (now - lastMqttAttempt > 5000) {
      lastMqttAttempt = now;
      Serial.print("MQTT connect... ");
      if (mqttClient.connect(MQTT_CLIENT)) {
        Serial.println("OK");
      } else {
        Serial.print("failed rc="); Serial.println(mqttClient.state());
      }
    }
  }
  mqttClient.loop();

  // Publish on interval
  unsigned long now = millis();
  if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
    lastPublish = now;

    float temp = dht.readTemperature();
    float rh   = dht.readHumidity();

    if (isnan(temp) || isnan(rh)) {
      Serial.println("DHT22 read failed - skipping publish");
    } else {
      Serial.print("Temp="); Serial.print(temp, 1); Serial.print(" C  ");
      Serial.print("RH=");   Serial.print(rh,   1); Serial.println(" %");

      if (mqttClient.connected()) {
        char payload[48];
        snprintf(payload, sizeof(payload), "{\"temp\":%.1f,\"rh\":%.1f}", temp, rh);
        bool ok = mqttClient.publish(MQTT_TOPIC, payload);
        Serial.print("MQTT publish "); Serial.print(payload);
        Serial.println(ok ? " OK" : " FAILED");
      }
    }
  }
}
