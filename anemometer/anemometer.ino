/*
  Anemometer (4-20 mA) analog reader + MQTT publisher
  Target board: Wemos D1 mini (ESP8266)

  --- Anemometer ---
  The anemometer outputs a 4-20 mA current loop; a 250 Ohm sense resistor
  converts this to 1-5 V. A voltage divider (5:1) scales this down to
  0-1 V for the Wemos D1 mini A0 pin (10-bit ADC).

  Conversion:
    V_adc   = ADC * (ADC_VREF / ADC_MAX)
    V_sense = V_adc * VOLTAGE_DIVIDER_RATIO
    I_mA    = (V_sense / SENSE_RESISTOR_OHMS) * 1000

  Wind speed mapping (linear):
    ADC = 300  (4 mA)   -> 0 m/s
    ADC = 1024 (20 mA)  -> 30 m/s

  --- MQTT ---
  Publishes JSON to obsybox/anemometer every 10 s:
    {"wind":3.7}
  WiFi credentials loaded from arduino_secrets.h.
*/

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Ticker.h>
#include "arduino_secrets.h"

// --- Network / MQTT settings --------------------------------------------
const char*   MQTT_SERVER  = "192.168.1.49";
const int     MQTT_PORT    = 1883;
const char*   MQTT_TOPIC   = "obsybox/anemometer";
const char*   MQTT_CLIENT  = "Anemometer_ESP8266";

// Static IP 
IPAddress staticIP(192, 168, 1, 73);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// Watchdog: restart if loop stalls for > 30 s
Ticker watchdog;
void watchdogReset() { Serial.println("Watchdog timeout - restarting"); ESP.restart(); }
void feedWatchdog()  { watchdog.detach(); watchdog.once(30, watchdogReset); }

// Publish interval
const unsigned long PUBLISH_INTERVAL_MS = 10000UL;  // 10 seconds
unsigned long lastPublish = 0;
unsigned long lastMqttAttempt = 0;

// --- User-configurable constants ----------------------------------------
const int ADC_MAX = 1023;                 // 10-bit ADC: 0..1023
const float ADC_VREF = 1.0;               // V measured at A0 (Wemos A0 ~1.0V)
const float SENSE_RESISTOR_OHMS = 250.0;   // 250 Ohm sense resistor
// Ratio: V_sense / V_adc. Default 5.0 assumes a 4:1 divider (5V -> 1V).
const float VOLTAGE_DIVIDER_RATIO = 5.0;

// Wind speed calibration: ADC endpoints for 0 m/s and 30 m/s
// 4 mA (0 m/s) -> 1 V at sense resistor -> 1/5 of full-scale ADC
// 20 mA (30 m/s) -> 5 V at sense resistor -> full-scale ADC
const float WIND_ADC_MIN  = 300.0;          // measured ADC count at 0 m/s (4 mA)
const float WIND_ADC_MAX  = 1024.0;         // full scale (20 mA, 30 m/s)
const float WIND_MAX_MS   = 30.0;           // m/s at 20 mA

// --- Setup ---------------------------------------------------------------
void setup() {
  Serial.begin(9600);
  Serial.println("\nAnemometer starting");

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

  // Read and calculate wind speed
  int adc = analogRead(A0);

  // Voltage at the ADC pin (volts)
  float v_adc = (float)adc * (ADC_VREF / (float)ADC_MAX);

  // Reconstruct the actual voltage across the sense resistor
  float v_sense = v_adc * VOLTAGE_DIVIDER_RATIO;

  // Current in milliamps
  float current_mA = (v_sense / SENSE_RESISTOR_OHMS) * 1000.0;

  // Wind speed: linear interpolation between 4 mA (0 m/s) and 20 mA (30 m/s)
  float wind_ms = (float(adc) - WIND_ADC_MIN) / (WIND_ADC_MAX - WIND_ADC_MIN) * WIND_MAX_MS;
  wind_ms = constrain(wind_ms, 0.0, WIND_MAX_MS);

  // Print a concise, human-readable line
  //Serial.print("ADC="); Serial.print(adc);
  //Serial.print("  V_adc="); Serial.print(v_adc, 3); Serial.print("V");
  //Serial.print("  V_sense="); Serial.print(v_sense, 3); Serial.print("V");
  //Serial.print("  I="); Serial.print(current_mA, 2); Serial.print(" mA");
  //Serial.print("  Wind="); Serial.print(wind_ms, 1); Serial.println(" m/s");

  // Publish to MQTT every PUBLISH_INTERVAL_MS
  unsigned long now = millis();
  if (mqttClient.connected() && (now - lastPublish >= PUBLISH_INTERVAL_MS)) {
    lastPublish = now;
    char payload[24];
    snprintf(payload, sizeof(payload), "{\"wind\": %.1f}", wind_ms);
    bool ok = mqttClient.publish(MQTT_TOPIC, payload);
    Serial.print("MQTT publish "); Serial.print(payload);
    Serial.println(ok ? " OK" : " FAILED");
  }

  delay(200);
}
