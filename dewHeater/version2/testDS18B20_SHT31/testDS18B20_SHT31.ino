// Test DS18B20 and SHT31 on Arduino UNO
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <Adafruit_SHT31.h>

#define ONE_WIRE_BUS 12 //18B20 data pin connected to digital pin 12

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature ds18b20(&oneWire);
Adafruit_SHT31 sht31 = Adafruit_SHT31();

void setup() {
  Serial.begin(9600);
  Serial.println("starting");
  delay(1000);

  // DS18B20 setup
  ds18b20.begin();
  Serial.println("ds strted");
  // SHT31 setup
  Wire.begin();
  if (!sht31.begin(0x44)) { // 0x44 is the default I2C address for SHT31
    Serial.println("Couldn't find SHT31 sensor at 0x44. Check wiring!");
  } else {
    Serial.println("SHT31 sensor found.");
  }
  Serial.println("end of loop");
}

void loop() {
  // DS18B20 reading
  ds18b20.requestTemperatures();
  float dsTemp = ds18b20.getTempCByIndex(0);

  Serial.print("DS18B20 Temperature: ");
  if (dsTemp == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor not found");
  } else {
    Serial.print(dsTemp);
    Serial.println(" °C");
  }

  // SHT31 reading
  float shtTemp = sht31.readTemperature();
  float shtHum = sht31.readHumidity();

  Serial.print("SHT31 Temperature: ");
  Serial.print(shtTemp);
  Serial.print(" °C, Humidity: ");
  Serial.print(shtHum);
  Serial.println(" %");

  Serial.println("--------------------------");
  delay(2000); // Wait 2 seconds before next reading
}
// This code reads temperature from a DS18B20 sensor and temperature/humidity from an SHT31 sensor.
// It prints the readings to the Serial Monitor every 2 seconds.
// Make sure to connect the DS18B20 data pin to digital pin 2 and the SHT31 sensor to the I2C bus (SDA to A4, SCL to A5 on Arduino UNO).
// Ensure you have the required libraries installed: DallasTemperature and Adafruit_SHT31.
// You can install these libraries via the Library Manager in the Arduino IDE.