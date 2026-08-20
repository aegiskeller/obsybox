/*
 * I2C Scanner for Arduino Uno
 * Use this to verify MLX90614 sensor hardware
 * 
 * Hardware Connections for Arduino Uno:
 * MLX90614 VIN -> 5V (or 3.3V)
 * MLX90614 GND -> GND
 * MLX90614 SCL -> A5
 * MLX90614 SDA -> A4
 * 
 * Expected device:
 * - MLX90614: 0x5A
 */

#include <Wire.h>

void setup() {
  Serial.begin(9600);
  while (!Serial);
  delay(100);
  
  Serial.println("\n=== I2C Scanner for Arduino Uno ===");
  Serial.println("SDA: A4, SCL: A5");
  
  Wire.begin();  // Arduino Uno uses default pins (A4/A5)
  Serial.println("I2C initialized. Starting scan...\n");
}

void loop() {
  byte error, address;
  int nDevices = 0;

  Serial.println("Scanning I2C bus (addresses 0x01 to 0x7F)...");
  Serial.println("-------------------------------------------");

  for (address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0) {
      Serial.print("Device found at address 0x");
      if (address < 16) {
        Serial.print("0");
      }
      Serial.print(address, HEX);
      
      // Identify common I2C devices
      if (address == 0x5A) {
        Serial.print(" <-- MLX90614 IR Sensor (THIS IS WHAT WE WANT!)");
      } else if (address == 0x29) {
        Serial.print(" (TSL2591 Light Sensor)");
      } else if (address == 0x39) {
        Serial.print(" (TSL2561 Light Sensor)");
      } else if (address == 0x76 || address == 0x77) {
        Serial.print(" (BME280/BMP280 Pressure Sensor)");
      } else if (address == 0x40) {
        Serial.print(" (HTU21D/SI7021 Humidity Sensor)");
      } else if (address == 0x44) {
        Serial.print(" (SHT31 Humidity Sensor)");
      } else if (address == 0x48) {
        Serial.print(" (ADS1115 ADC)");
      } else if (address == 0x68) {
        Serial.print(" (DS3231 RTC or MPU6050 IMU)");
      }
      
      Serial.println();
      nDevices++;
    } else if (error == 4) {
      Serial.print("Unknown error at address 0x");
      if (address < 16) {
        Serial.print("0");
      }
      Serial.println(address, HEX);
    }
  }

  Serial.println("-------------------------------------------");
  if (nDevices == 0) {
    Serial.println("No I2C devices found!");
    Serial.println("\nTroubleshooting:");
    Serial.println("  1. Check wiring:");
    Serial.println("     MLX90614 VIN -> Arduino 5V (or 3.3V)");
    Serial.println("     MLX90614 GND -> Arduino GND");
    Serial.println("     MLX90614 SCL -> Arduino A5");
    Serial.println("     MLX90614 SDA -> Arduino A4");
    Serial.println("  2. MLX90614 has internal pull-ups (no external resistors needed)");
    Serial.println("  3. Try different power (5V vs 3.3V)");
    Serial.println("  4. Check for loose connections");
    Serial.println("  5. Sensor may be damaged/faulty");
  } else {
    Serial.print("Found ");
    Serial.print(nDevices);
    Serial.println(" device(s)");
  }

  Serial.println("\nScanning again in 5 seconds...\n");
  delay(5000);
}
