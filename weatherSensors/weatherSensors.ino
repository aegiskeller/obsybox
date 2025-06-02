#include <DHT.h>

// Pin definitions
#define DHTPIN D4        // DHT11 data pin connected to NodeMCU D4 
#define DHTTYPE DHT11     // DHT 11
#define LIGHT_SENSOR_PIN A0 // Light sensor connected to analog pin A0

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(LIGHT_SENSOR_PIN, INPUT);
}

void loop() {
  // Read temperature as Celsius
  float temperature = dht.readTemperature();
  // Read humidity
  float humidity = dht.readHumidity();
  // Read light sensor value
  int lightValue = analogRead(LIGHT_SENSOR_PIN);

  // Check if any reads failed
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Failed to read from DHT sensor!");
  } else {
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.print(" °C, Humidity: ");
    Serial.print(humidity);
    Serial.print(" %, Light: ");
    Serial.println(lightValue);
  }

  delay(2000); // Wait 2 seconds between readings
}