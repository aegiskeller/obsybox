#include <Arduino.h>
#include <Wire.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>
#include <Adafruit_MLX90614.h>
#include "arduino_secrets.h"

// WiFi credentials
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

// MQTT settings
const char* mqtt_server = MQTT_SERVER;
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/opir_sensor";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// Sensor objects
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

// Non-blocking MQTT reconnect variables
unsigned long lastMqttReconnectAttempt = 0;
const unsigned long mqttReconnectInterval = 5000; // 5 seconds between attempts

// Sensor error flags
bool tslSensorOk = false;
bool mlxSensorOk = false;

// TSL2591 adaptive gain variables
tsl2591Gain_t currentGain = TSL2591_GAIN_MED;
unsigned long lastGainCheck = 0;
const unsigned long gainCheckInterval = 30000; // Check gain every 30 seconds
const uint8_t LIGHT_AVERAGE_SAMPLES = 10;
uint8_t lightSampleCount = 0;
uint8_t lightSampleIndex = 0;
uint32_t lightSamples[LIGHT_AVERAGE_SAMPLES];
uint32_t lightAverage = 0;
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("TSL2591, MLX90614 ");

  Wire.begin();

  WiFi.mode(WIFI_STA);

  // Static IP configuration 
  IPAddress local_IP(192, 168, 1, 101);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  //IPAddress dns(8, 8, 8, 8);
  WiFi.config(local_IP, gateway, subnet);

  int attempts = 0;
  const int maxAttempts = 3;
  
  while (attempts < maxAttempts) {
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi (attempt " + String(attempts + 1) + "/" + String(maxAttempts) + ")");
    
    unsigned long wifiStartTime = millis();
    while (WiFi.status() != WL_CONNECTED) {
      if (millis() - wifiStartTime > 20000) { // 20 second timeout per attempt
        Serial.println("\nWiFi connection timeout.");
        WiFi.disconnect();
        delay(1000);
        break;
      }
      delay(500);
      Serial.print(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      break;
    }
    
    attempts++;
    if (attempts >= maxAttempts) {
      Serial.println("\nAll WiFi connection attempts failed. Continuing without reset.");
    }
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setBufferSize(512);

  // Try to initialize sensors - no blocking loops
  tslSensorOk = tsl.begin();
  if (!tslSensorOk) {
    Serial.println("TSL2591 not found. Check wiring!");
  }
  
  mlxSensorOk = mlx.begin();
  if (!mlxSensorOk) {
    Serial.println("MLX90614 not found. Check wiring!");
  }

  // Only configure sensors that are present
  if (tslSensorOk) {
    currentGain = TSL2591_GAIN_MED;
    tsl.setGain(currentGain);
    tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);
    Serial.println("TSL2591 initialized with medium gain");
  }
}

// Adaptive gain control for TSL2591
void adaptTSLGain() {
  if (!tslSensorOk) return;

  // Read the current raw channels and feed them into a rolling average.
  uint32_t lum = tsl.getFullLuminosity();
  uint16_t ir = lum >> 16;
  uint16_t full = lum & 0xFFFF;

  // Saturated or invalid readings can produce bogus values (e.g. 0, very low,
  // or values that look like over-range). Treat those as unreliable and avoid
  // immediately jumping back to the most sensitive gain.
  bool invalidReading = (full == 0 && ir == 0) || (full >= 0xFFFE) || (ir >= 0xFFFE);
  if (invalidReading) {
    full = 0;
    ir = 0;
  }

  lightSamples[lightSampleIndex] = full;
  lightSampleIndex = (lightSampleIndex + 1) % LIGHT_AVERAGE_SAMPLES;

  if (lightSampleCount < LIGHT_AVERAGE_SAMPLES) {
    lightSampleCount++;
  }

  // Wait until we have a full window of samples before changing gain.
  if (lightSampleCount < LIGHT_AVERAGE_SAMPLES) {
    return;
  }

  uint32_t sum = 0;
  for (uint8_t i = 0; i < LIGHT_AVERAGE_SAMPLES; i++) {
    sum += lightSamples[i];
  }
  lightAverage = sum / LIGHT_AVERAGE_SAMPLES;

  tsl2591Gain_t newGain = currentGain;
  tsl2591IntegrationTime_t newTiming = TSL2591_INTEGRATIONTIME_100MS;

  bool saturated = (lightAverage >= 45000) || (ir >= 45000);

  if (saturated) {
    newGain = TSL2591_GAIN_LOW;
    newTiming = TSL2591_INTEGRATIONTIME_100MS;
  }
  else if (currentGain == TSL2591_GAIN_LOW) {
    if (lightAverage <= 10000) {
      newGain = TSL2591_GAIN_MED;
      newTiming = TSL2591_INTEGRATIONTIME_200MS;
    }
  }
  else if (currentGain == TSL2591_GAIN_MED) {
    if (lightAverage >= 22000) {
      newGain = TSL2591_GAIN_LOW;
      newTiming = TSL2591_INTEGRATIONTIME_100MS;
    }
    else if (lightAverage <= 4000) {
      newGain = TSL2591_GAIN_HIGH;
      newTiming = TSL2591_INTEGRATIONTIME_300MS;
    }
  }
  else if (currentGain == TSL2591_GAIN_HIGH) {
    if (lightAverage >= 14000) {
      newGain = TSL2591_GAIN_MED;
      newTiming = TSL2591_INTEGRATIONTIME_200MS;
    }
    else if (lightAverage <= 1500) {
      // Don't jump to MAX immediately after a noisy or invalid low reading.
      // Stay on HIGH until the average is clearly very dark.
      newGain = TSL2591_GAIN_HIGH;
      newTiming = TSL2591_INTEGRATIONTIME_300MS;
    }
  }
  else { // TSL2591_GAIN_MAX
    if (lightAverage >= 5000) {
      newGain = TSL2591_GAIN_HIGH;
      newTiming = TSL2591_INTEGRATIONTIME_300MS;
    }
  }

  if (newGain != currentGain) {
    currentGain = newGain;
    tsl.setGain(currentGain);
    tsl.setTiming(newTiming);

    delay(120);

    String gainStr;
    switch (currentGain) {
      case TSL2591_GAIN_LOW: gainStr = "LOW (1x)"; break;
      case TSL2591_GAIN_MED: gainStr = "MED (25x)"; break;
      case TSL2591_GAIN_HIGH: gainStr = "HIGH (428x)"; break;
      case TSL2591_GAIN_MAX: gainStr = "MAX (9876x)"; break;
      default: gainStr = "UNKNOWN"; break;
    }

    Serial.print("TSL2591 gain adjusted to ");
    Serial.print(gainStr);
    Serial.print(" (avg full was ");
    Serial.print(lightAverage);
    Serial.println(")");
  }
}

unsigned long lastMqttPublish = 0;

void loop() {
  // Non-blocking MQTT reconnection
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    
    if (now - lastMqttReconnectAttempt > mqttReconnectInterval) {
      lastMqttReconnectAttempt = now;
      Serial.print("Attempting MQTT connection...");
      if (mqttClient.connect("OPIR_ESP8266")) {
        Serial.println("connected");
      } else {
        Serial.print("failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" will try again in 5 seconds");
      }
    }
  } else {
    mqttClient.loop();
  }
  
  // Try to reinitialize failed sensors periodically
  static unsigned long lastSensorCheck = 0;
  if (millis() - lastSensorCheck > 60000) { // Check every minute
    lastSensorCheck = millis();
    
    if (!tslSensorOk) {
      tslSensorOk = tsl.begin();
      if (tslSensorOk) {
        Serial.println("TSL2591 sensor reconnected");
        currentGain = TSL2591_GAIN_MED;
        tsl.setGain(currentGain);
        tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);
      }
    }
    
    if (!mlxSensorOk) {
      mlxSensorOk = mlx.begin();
      if (mlxSensorOk) {
        Serial.println("MLX90614 sensor reconnected");
      }
    }
  }

  // Adaptive gain control for TSL2591
  if (millis() - lastGainCheck > gainCheckInterval) {
    lastGainCheck = millis();
    adaptTSLGain();
  }

  unsigned long now = millis();

  // Publish to MQTT every minute
  if (now - lastMqttPublish >= 60000 || lastMqttPublish == 0) {
    // Default values
    float lux = 0.0;
    float objTemp = 0.0;
    float ambTemp = 0.0;
    uint16_t ir = 0;
    uint16_t full = 0;
    
    // Read sensors if available
    if (tslSensorOk) {
      uint32_t lum = tsl.getFullLuminosity();
      ir = lum >> 16;
      full = lum & 0xFFFF;

      lux = tsl.calculateLux(full, ir);
      if (isnan(lux)) lux = 0.0;
    }
    
    if (mlxSensorOk) {
      objTemp = mlx.readObjectTempC();
      ambTemp = mlx.readAmbientTempC();
    }

    char payload[256];
    snprintf(payload, sizeof(payload),
      "{\"lux\":%.2f,\"sky\":%.2f,\"ambient\":%.2f,\"tsl_gain\":%d}",
      lux, objTemp, ambTemp, (int)currentGain);

    // Print sensor values to serial
    Serial.println("--- Sensor Reading ---");
    Serial.print("Lux: "); Serial.println(lux, 2);
    Serial.print("Sky Temp: "); Serial.print(objTemp, 2); Serial.println(" °C");
    Serial.print("Ambient Temp: "); Serial.print(ambTemp, 2); Serial.println(" °C");
    
    String gainStr = "N/A";
    if (tslSensorOk) {
      switch (currentGain) {
        case TSL2591_GAIN_LOW: gainStr = "LOW (1x)"; break;
        case TSL2591_GAIN_MED: gainStr = "MED (25x)"; break;
        case TSL2591_GAIN_HIGH: gainStr = "HIGH (428x)"; break;
        case TSL2591_GAIN_MAX: gainStr = "MAX (9876x)"; break;
      }
    }
    Serial.print("TSL Gain: "); Serial.println(gainStr);
    Serial.println("----------------------");

    // Only publish if MQTT is connected
    if (mqttClient.connected()) {
      mqttClient.publish(mqtt_topic, payload);
      Serial.println("MQTT data published");
    } else {
      Serial.println("MQTT not connected - data not published");
    }

    lastMqttPublish = now;
  }
}