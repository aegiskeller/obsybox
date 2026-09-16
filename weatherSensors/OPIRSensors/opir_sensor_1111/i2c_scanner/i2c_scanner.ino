/*
 * I2C Scanner for ESP8266
 * Use this to verify what devices are on the I2C bus
 * 
 * Expected devices:
 * - MLX90614: 0x5A
 * - TSL2591: 0x29
 */

#include <Wire.h>

#define I2C_SDA 4  // D2
#define I2C_SCL 5  // D1

void setup() {
  Serial.begin(115200);
  while (!Serial);
  delay(100);
  
  Serial.println("\n=== I2C Scanner for ESP8266 ===");
  Serial.println("SDA: D2 (GPIO4), SCL: D1 (GPIO5)");
  
  Wire.begin(I2C_SDA, I2C_SCL);
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
      if (address == 0x29) {
        Serial.print(" (TSL2591 Light Sensor - EXPECTED)");
      } else if (address == 0x5A) {
        Serial.print(" (MLX90614 IR Sensor - EXPECTED)");
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
    Serial.println("  1. Check wiring (SDA, SCL, VCC, GND)");
    Serial.println("  2. Verify 3.3V power supply");
    Serial.println("  3. Check for 4.7kΩ pull-up resistors on SDA/SCL");
    Serial.println("  4. Try swapping SDA and SCL pins");
  } else {
    Serial.print("Found ");
    Serial.print(nDevices);
    Serial.println(" device(s)");
    
    Serial.println("\nExpected devices:");
    Serial.println("  MLX90614 (IR Temp): 0x5A");
    Serial.println("  TSL2591 (Light):    0x29");
  }

  Serial.println("\nScanning again in 5 seconds...\n");
  delay(5000);
}
