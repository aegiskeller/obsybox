#include <Wire.h>
#include <WiFiNINA.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>
#include <Adafruit_MLX90614.h>
#include <Adafruit_AHTX0.h>
#include <ArduinoMqttClient.h>
#include "arduino_secrets.h"
#include <Arduino.h>
#include <Adafruit_SleepyDog.h>

// WiFi credentials
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;

// MQTT settings
const char* mqtt_server = SECRET_MQTT_SERVER;
const int mqtt_port = 1883;
const char* mqtt_topic = "obsybox/opir_sensor";

WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Sensor objects
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
Adafruit_AHTX0 aht10;

WiFiServer server(80);

// Non-blocking MQTT reconnect variables
unsigned long lastMqttReconnectAttempt = 0;
const unsigned long mqttReconnectInterval = 5000; // 5 seconds between attempts
unsigned long mqttFirstDisconnectTime = 0;
const unsigned long mqttResetTimeout = 180000; // 3 minutes - reset if MQTT stuck

// Sensor error flags
bool tslSensorOk = false;
bool mlxSensorOk = false;
bool ahtSensorOk = false;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("TSL2591, MLX90614 & AHT10 (MKR WiFi)");

  Wire.begin();

  // Enable watchdog first thing
  Watchdog.enable(30000); // 30 seconds timeout

  // Static IP configuration 
  IPAddress local_IP(192, 168, 1, 101);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  //IPAddress dns(8, 8, 8, 8);
  WiFi.config(local_IP, gateway, subnet);

  // WiFi connection with hardware reset
  int attempts = 0;
  const int maxAttempts = 3;
  
  while (attempts < maxAttempts) {
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi (attempt " + String(attempts + 1) + "/" + String(maxAttempts) + ")");
    
    unsigned long wifiStartTime = millis();
    while (WiFi.status() != WL_CONNECTED) {
      if (millis() - wifiStartTime > 20000) { // 20 second timeout per attempt
        Serial.println("\nWiFi connection timeout.");
        WiFi.end();  // Clean up before next attempt
        delay(1000);
        break;
      }
      delay(500);
      Serial.print(".");
      Watchdog.reset();
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      break;  // Successfully connected
    }
    
    attempts++;
    if (attempts >= maxAttempts) {
      Serial.println("\nAll WiFi connection attempts failed. Performing hardware reset...");
      delay(1000);
      NVIC_SystemReset();  // Force hardware reset
    }
  }
  Serial.println("\nWiFi connected. IP address: ");
  Serial.println(WiFi.localIP());

  mqttClient.setId("OPIR_MKRWiFi");
  // We'll handle MQTT connection in the loop

  // Try to initialize sensors - no blocking loops
  tslSensorOk = tsl.begin();
  if (!tslSensorOk) {
    Serial.println("TSL2591 not found. Check wiring!");
  }
  
  mlxSensorOk = mlx.begin();
  if (!mlxSensorOk) {
    Serial.println("MLX90614 not found. Check wiring!");
  }
  
  ahtSensorOk = aht10.begin();
  if (!ahtSensorOk) {
    Serial.println("AHT10 not found. Check wiring!");
  }

  // Only configure sensors that are present
  if (tslSensorOk) {
    tsl.setGain(TSL2591_GAIN_MED);
    tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);
  }

  server.begin();
  Serial.println("HTTP server started");
}

void serveClient(WiFiClient& client) {
  String req = client.readStringUntil('\r');
  client.flush();

  // Default values in case sensors are not available
  float lux = 0.0;
  float objTemp = 0.0;
  float ambTemp = 0.0;
  float ahtTemp = 0.0;
  float ahtHum = 0.0;
  uint16_t ir = 0;
  uint16_t full = 0;

  // Read sensor values only if sensors are available
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
  
  if (ahtSensorOk) {
    sensors_event_t humidity, temp;
    aht10.getEvent(&humidity, &temp);
    ahtTemp = temp.temperature;
    ahtHum = humidity.relative_humidity;
  }

  // Check for API endpoints
  if (req.indexOf("GET /lux") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(lux, 2);
    return;
  }
  
  if (req.indexOf("GET /sky") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(objTemp, 2);
    return;
  }
  
  if (req.indexOf("GET /ambient") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(ambTemp, 2);
    return;
  }
  
  if (req.indexOf("GET /aht_temp") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(ahtTemp, 2);
    return;
  }
  
  if (req.indexOf("GET /aht_humidity") >= 0) {
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println(ahtHum, 2);
    return;
  }

  // Serve main HTML page for root path
  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html");
  client.println("Connection: close");
  client.println();
  client.println(R"rawliteral(
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset='utf-8'>
      <title>Sky Condition Sensors</title>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <style>
        body { background: #181c24; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; }
        h1 { color: #ffd600; }
        .info { background: #232837; color: #b0b8c0; border-radius: 8px; padding: 18px 24px; max-width: 400px; margin: 32px auto; font-size: 1.2em; }
        .label { color: #ffd600; }
      </style>
    </head>
    <body>
      <h1>Sky Condition Sensors</h1>
      <div class='info'>)rawliteral");
  
  // Only show data for available sensors
  if (tslSensorOk) {
    client.println("<div><span class='label'>Lux:</span> " + String(lux, 2) + "</div>");
  } else {
    client.println("<div><span class='label'>Lux:</span> <i>Sensor Error</i></div>");
  }
  
  if (mlxSensorOk) {
    client.println("<div><span class='label'>Sky Temp:</span> " + String(objTemp, 2) + " &deg;C</div>");
    client.println("<div><span class='label'>Ambient Temp:</span> " + String(ambTemp, 2) + " &deg;C</div>");
  } else {
    client.println("<div><span class='label'>Sky Temp:</span> <i>Sensor Error</i></div>");
    client.println("<div><span class='label'>Ambient Temp:</span> <i>Sensor Error</i></div>");
  }
  
  if (ahtSensorOk) {
    client.println("<div><span class='label'>AHT10 Temp:</span> " + String(ahtTemp, 2) + " &deg;C</div>");
    client.println("<div><span class='label'>AHT10 Humidity:</span> " + String(ahtHum, 2) + " %</div>");
  } else {
    client.println("<div><span class='label'>AHT10 Temp:</span> <i>Sensor Error</i></div>");
    client.println("<div><span class='label'>AHT10 Humidity:</span> <i>Sensor Error</i></div>");
  }

  client.println(R"rawliteral(
      </div>
      <div style="text-align:center;margin-top:2em;">
        <small><em>Sensors: TSL2591 (lux), MLX90614 (sky/ambient temperature), AHT10 (temp/humidity)</em></small><br>
        <small><em>API endpoints: /lux /sky /ambient /aht_temp /aht_humidity</em></small>
      </div>
    </body>
    </html>
  )rawliteral");
}

unsigned long lastMqttPublish = 0;

void loop() {
  // Reset watchdog at the start of the loop
  Watchdog.reset();
  
  // Non-blocking MQTT reconnection
  if (!mqttClient.connected()) {
    unsigned long now = millis();
    
    // Track when MQTT first disconnected
    if (mqttFirstDisconnectTime == 0) {
      mqttFirstDisconnectTime = now;
      Serial.println("MQTT disconnected - starting timeout timer");
    }
    
    // Check if MQTT has been disconnected too long
    if (now - mqttFirstDisconnectTime > mqttResetTimeout) {
      Serial.println("MQTT stuck for more than 3 minutes. Forcing hardware reset...");
      delay(1000); // Give serial time to send
      NVIC_SystemReset(); // Force hardware reset
    }
    
    if (now - lastMqttReconnectAttempt > mqttReconnectInterval) {
      lastMqttReconnectAttempt = now;
      Serial.print("Attempting MQTT connection...");
      mqttClient.setId("OPIR_MKRWiFi");
      if (mqttClient.connect(mqtt_server, mqtt_port)) {
        Serial.println("connected");
        mqttFirstDisconnectTime = 0; // Reset timeout timer on successful connection
      } else {
        Serial.print("failed, rc=");
        Serial.print(mqttClient.connectError());
        Serial.println(" will try again in 5 seconds");
      }
    }
  } else {
    // MQTT is connected - reset the disconnect timer
    mqttFirstDisconnectTime = 0;
    mqttClient.poll();
  }
  
  // Try to reinitialize failed sensors periodically
  static unsigned long lastSensorCheck = 0;
  if (millis() - lastSensorCheck > 60000) { // Check every minute
    lastSensorCheck = millis();
    
    if (!tslSensorOk) {
      tslSensorOk = tsl.begin();
      if (tslSensorOk) {
        Serial.println("TSL2591 sensor reconnected");
        tsl.setGain(TSL2591_GAIN_MED);
        tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);
      }
    }
    
    if (!mlxSensorOk) {
      mlxSensorOk = mlx.begin();
      if (mlxSensorOk) {
        Serial.println("MLX90614 sensor reconnected");
      }
    }
    
    if (!ahtSensorOk) {
      ahtSensorOk = aht10.begin();
      if (ahtSensorOk) {
        Serial.println("AHT10 sensor reconnected");
      }
    }
  }

  // Handle HTTP requests
  WiFiClient client = server.available();
  if (client) {
    serveClient(client);
    delay(1);
    client.stop();
  }

  unsigned long now = millis();

  // Publish to MQTT every minute
  if (now - lastMqttPublish >= 60000 || lastMqttPublish == 0) {
    // Default values
    float lux = 0.0;
    float objTemp = 0.0;
    float ambTemp = 0.0;
    float ahtTemp = 0.0;
    float ahtHum = 0.0;
    uint16_t ir = 0;
    uint16_t full = 0;
    
    // Read sensors if available
    if (tslSensorOk) {
if (tslSensorOk) {
  uint32_t lum = tsl.getFullLuminosity();
  ir = lum >> 16;
  full = lum & 0xFFFF;
  
  // Check for saturation (max value is 0xFFFF for full spectrum)
  if (full >= 0xFFFF || ir >= 0xFFFF) {
    // Saturated - reduce gain or integration time
    tsl.setGain(TSL2591_GAIN_LOW);
    tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS);
  } else if (full < 100) {
    // Too dark - increase sensitivity
    tsl.setGain(TSL2591_GAIN_HIGH);
    tsl.setTiming(TSL2591_INTEGRATIONTIME_300MS);
  }
  
  lux = tsl.calculateLux(full, ir);
  if (isnan(lux)) lux = 0.0;
}    }
    
    if (mlxSensorOk) {
      objTemp = mlx.readObjectTempC();
      ambTemp = mlx.readAmbientTempC();
    }
    
    if (ahtSensorOk) {
      sensors_event_t humidity, temp;
      aht10.getEvent(&humidity, &temp);
      ahtTemp = temp.temperature;
      ahtHum = humidity.relative_humidity;
    }

    char payload[256];
    snprintf(payload, sizeof(payload),
      "{\"lux\":%.2f,\"sky\":%.2f,\"ambient\":%.2f,\"ir\":%u,\"full\":%u,\"aht_temp\":%.2f,\"aht_hum\":%.2f}",
      lux, objTemp, ambTemp, ir, full, ahtTemp, ahtHum);

    // Print sensor values to serial
    Serial.println("--- Sensor Reading ---");
    Serial.print("Lux: "); Serial.println(lux, 2);
    Serial.print("Sky Temp: "); Serial.print(objTemp, 2); Serial.println(" °C");
    Serial.print("Ambient Temp: "); Serial.print(ambTemp, 2); Serial.println(" °C");
    Serial.print("IR: "); Serial.println(ir);
    Serial.print("Full: "); Serial.println(full);
    Serial.print("AHT10 Temp: "); Serial.print(ahtTemp, 2); Serial.println(" °C");
    Serial.print("AHT10 Humidity: "); Serial.print(ahtHum, 2); Serial.println(" %");
    Serial.println("----------------------");

    // Only publish if MQTT is connected
    if (mqttClient.connected()) {
      mqttClient.beginMessage(mqtt_topic);
      mqttClient.print(payload);
      mqttClient.endMessage();
      Serial.println("MQTT data published");
    } else {
      Serial.println("MQTT not connected - data not published");
    }

    lastMqttPublish = now;
  }

  // Reset watchdog at the end of the loop
  Watchdog.reset();
}