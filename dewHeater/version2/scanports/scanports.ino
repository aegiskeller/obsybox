#include <Wire.h>

void setup() {
  Wire.begin();
  Serial.begin(9600);
  while (!Serial);
  Serial.println("\nBME180 I2C Address Scanner");
}

void loop() {
  byte error;
  byte address = 0x77; // BME180 default I2C address

  Wire.beginTransmission(address);
  error = Wire.endTransmission();

  if (error == 0) {
    Serial.println("BME180 found at address 0x77!");
  } else {
    Serial.println("BME180 NOT found at address 0x77.");
  }

  delay(5000);
}