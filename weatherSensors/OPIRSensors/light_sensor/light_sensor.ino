/*
 * TSL2591 Light Sensor with WiFi and MQTT for Lolin ESP8266 (D1 Mini)
 * 
 * Strategy: Read sensor FIRST, then transmit via WiFi/MQTT
 * This separates I2C operations from WiFi activity to avoid interference
 * 
 * Hardware Connections:
 * TSL2591 VIN -> 3.3V
 * TSL2591 GND -> GND
 * TSL2591 SCL -> D1 (GPIO5)
 * TSL2591 SDA -> D2 (GPIO4)
 * 
 * Required Libraries:
 * - Adafruit_TSL2591
 * - PubSubClient
 * - ESP8266WiFi (built-in)
 */

#include <Wire.h>
#include <Adafruit_TSL2591.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include "arduino_secrets.h"

// I2C pins for ESP8266
#define I2C_SDA 4  // D2
#define I2C_SCL 5  // D1

// WiFi and MQTT configuration from secrets file
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;
const char* mqtt_server = MQTT_SERVER;
const int mqtt_port = MQTT_PORT;
const char* mqtt_user = MQTT_USER;
const char* mqtt_pass = MQTT_PASS;

// Static IP configuration
IPAddress staticIP(STATIC_IP);
IPAddress gateway(GATEWAY_IP);
IPAddress subnet(SUBNET_MASK);
IPAddress dns(DNS_IP);

// Timing
unsigned long lastRead = 0;
const unsigned long READ_INTERVAL = 10000; // Read sensor every 10 seconds

// Sensor and network objects
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);
WiFiClient espClient;
PubSubClient mqtt(espClient);

// Data storage
uint16_t storedLux = 0;
uint16_t storedInfrared = 0;
uint16_t storedVisible = 0;
uint16_t storedFull = 0;
bool dataReady = false;

void setup() {
  Serial.begin(115200);
  delay(100);
  
  Serial.println("\nTSL2591 Light Sensor with MQTT");
  Serial.println("==============================");
  
  // Initialize I2C first
  Wire.begin(I2C_SDA, I2C_SCL);
  delay(100);
  
  // Initialize TSL2591 sensor
  Serial.print("Initializing TSL2591...");
  if (!tsl.begin()) {
    Serial.println("FAILED!");
    Serial.println("ERROR: Could not find TSL2591 sensor!");
    Serial.println("Check wiring:");
    Serial.println("  VIN -> 3.3V");
    Serial.println("  GND -> GND");
    Serial.println("  SCL -> D1 (GPIO5)");
    Serial.println("  SDA -> D2 (GPIO4)");
    Serial.println("I2C address should be 0x29");
    while (1) { delay(1000); }
  }
  Serial.println("OK!");
  
  // Configure sensor
  configureSensor();
  
  // Then connect WiFi
  connectWiFi();
  
  // Setup MQTT
  mqtt.setServer(mqtt_server, mqtt_port);
  
  Serial.println("Setup complete!");
  Serial.println();
}

void configureSensor() {
  // Configure gain and integration time
  // Medium gain (25x) and 100ms integration time for general use
  tsl.setGain(TSL2591_GAIN_MED);
  tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);
  
  Serial.println("TSL2591 Configuration:");
  Serial.print("  Gain: ");
  
  tsl2591Gain_t gain = tsl.getGain();
  switch(gain) {
    case TSL2591_GAIN_LOW:  Serial.println("1x (Low)"); break;
    case TSL2591_GAIN_MED:  Serial.println("25x (Medium) - Default"); break;
    case TSL2591_GAIN_HIGH: Serial.println("428x (High)"); break;
    case TSL2591_GAIN_MAX:  Serial.println("9876x (Max)"); break;
  }
  
  Serial.print("  Integration: ");
  Serial.print((tsl.getTiming() + 1) * 100, DEC);
  Serial.println(" ms");
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  
  WiFi.mode(WIFI_STA);
  WiFi.setSleepMode(WIFI_NONE_SLEEP);
  WiFi.config(staticIP, gateway, subnet, dns);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

void reconnectMQTT() {
  if (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    
    String clientId = "LightSensor-" + String(ESP.getChipId(), HEX);
    bool connected = false;
    
    if (strlen(mqtt_user) > 0) {
      connected = mqtt.connect(clientId.c_str(), mqtt_user, mqtt_pass);
    } else {
      connected = mqtt.connect(clientId.c_str());
    }
    
    if (connected) {
      Serial.println("connected!");
    } else {
      Serial.print("failed, rc=");
      Serial.println(mqtt.state());
    }
  }
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Step 1: Read sensor every 10 seconds
  if (currentMillis - lastRead >= READ_INTERVAL) {
    lastRead = currentMillis;
    
    Serial.println("Reading sensor...");
    
    // Get full luminosity (IR + Visible)
    uint32_t lum = tsl.getFullLuminosity();
    storedInfrared = lum >> 16;
    storedFull = lum & 0xFFFF;
    storedVisible = storedFull - storedInfrared;
    storedLux = tsl.calculateLux(storedFull, storedInfrared);
    
    dataReady = true;
    
    // Print to serial
    Serial.print("Lux: ");
    Serial.print(storedLux);
    Serial.print(" | IR: ");
    Serial.print(storedInfrared);
    Serial.print(" | Visible: ");
    Serial.print(storedVisible);
    Serial.print(" | Full: ");
    Serial.println(storedFull);
  }
  
  // Step 2: Transmit data after sensor read
  if (dataReady) {
    // Check WiFi
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi disconnected, reconnecting...");
      connectWiFi();
    }
    
    // Check MQTT
    if (!mqtt.connected()) {
      reconnectMQTT();
    }
    
    // Publish if connected
    if (mqtt.connected()) {
      String payload = "{\"Lux\":" + String(storedLux) + 
                      ",\"Infrared\":" + String(storedInfrared) +
                      ",\"Visible\":" + String(storedVisible) +
                      ",\"Full\":" + String(storedFull) + "}";
      
      if (mqtt.publish("obsybox/light_sensor", payload.c_str())) {
        Serial.println("Published: " + payload);
        dataReady = false; // Clear flag after successful publish
      } else {
        Serial.println("Publish failed!");
      }
    }
  }
  
  // Keep MQTT alive
  mqtt.loop();
  delay(100);
}
