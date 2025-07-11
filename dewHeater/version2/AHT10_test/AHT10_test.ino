#include <Wire.h>
#include <Adafruit_AHTX0.h>

Adafruit_AHTX0 aht;

void setup() {
  Serial.begin(9600);
  Wire.begin(2, 14); // SDA = D2, SCL = D14 for your board

  if (!aht.begin()) {
    Serial.println("Could not find AHT10/AHT20 sensor! Check wiring.");
    while (1) { yield(); }
  }
  Serial.println("AHT10/AHT20 sensor found.");
}

void loop() {
  sensors_event_t humidity, temp;
  aht.getEvent(&humidity, &temp); // Populate temp and humidity objects

  Serial.print("AHT10 Temperature: ");
  Serial.print(temp.temperature, 2);
  Serial.println(" °C");

  Serial.print("AHT10 Humidity: ");
  Serial.print(humidity.relative_humidity, 2);
  Serial.println(" %");

  Serial.println();
  delay(2000);
}