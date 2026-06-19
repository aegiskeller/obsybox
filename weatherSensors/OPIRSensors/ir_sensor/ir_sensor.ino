/*
 * MLX90614 IR Temperature Sensor with WiFi and MQTT
 * 
 * Strategy: Read sensor FIRST, then transmit via WiFi/MQTT
 * This separates I2C operations from WiFi activity to avoid interference
 * 
 * Hardware Connections:
 * MLX90614 VIN -> 3.3V
 * MLX90614 GND -> GND
 * MLX90614 SCL -> D1 (GPIO5)
 * MLX90614 SDA -> D2 (GPIO4)
 * 
 * Required Libraries:
 * - Adafruit_MLX90614
 * - PubSubClient
 */

#include <Wire.h>
#include <Adafruit_MLX90614.h>
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
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
WiFiClient espClient;
PubSubClient mqtt(espClient);

// Data storage
float storedAmbientTemp = 0.0;
float storedSkyTemp = 0.0;
bool dataReady = false;

void setup() {
  Serial.begin(115200);
  delay(100);
  
  Serial.println("\nMLX90614 IR Sensor with MQTT");
  Serial.println("==============================");
  
  // Initialize I2C first
  Wire.begin(I2C_SDA, I2C_SCL);
  
  if (!mlx.begin()) {
    Serial.println("ERROR: MLX90614 not found!");
    while (1) { delay(1000); }
  }
  Serial.println("MLX90614 initialized");
  
  // Then connect WiFi
  connectWiFi();
  
  // Setup MQTT
  mqtt.setServer(mqtt_server, mqtt_port);
  
  Serial.println("Setup complete!");
  Serial.println();
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  
  WiFi.mode(WIFI_STA);
  WiFi.config(staticIP, gateway, subnet, dns);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void reconnectMQTT() {
  if (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    
    String clientId = "IRSensor-" + String(ESP.getChipId(), HEX);
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
    storedAmbientTemp = mlx.readAmbientTempC();
    storedAmbientTemp = mlx.readAmbientTempC();
    storedSkyTemp = mlx.readObjectTempC();
    dataReady = true;
    
    Serial.print("AmbientTemp: ");
    Serial.print(storedAmbientTemp, 2);
    Serial.print(" °C | SkyTemp: ");
    Serial.print(storedSkyTemp, 2);
    Serial.println(" °C");
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
      String payload = "{\"AmbientTemp\":" + String(storedAmbientTemp, 2) + 
                      ",\"SkyTemp\":" + String(storedSkyTemp, 2) + "}";
      
      if (mqtt.publish("obsybox/ir_sensor", payload.c_str())) {
        Serial.println("Published: " + payload);
        dataReady = false; // Clear flag after successful publish
      } else {
        Serial.println("Publish failed!");
      }
    }
  }
  
  mqtt.loop();
  delay(100);
}
