#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>
#include <Adafruit_MLX90614.h>  // Add for GY-906 (MLX90614)

Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);
Adafruit_MLX90614 mlx = Adafruit_MLX90614(); // GY-906 object

void setup() {
  Serial.begin(115200);
  delay(100);

  Wire.begin(D2, D1); // For Wemos D1 mini: SDA = D2, SCL = D1

  if (tsl.begin()) {
    Serial.println("TSL2591 sensor found!");
  } else {
    Serial.println("No TSL2591 sensor found ... check your wiring!");
    while (1) delay(10);
  }

  if (mlx.begin()) {
    Serial.println("GY-906 (MLX90614) sensor found!");
  } else {
    Serial.println("No GY-906 (MLX90614) sensor found ... check your wiring!");
    while (1) delay(10);
  }

  tsl.setGain(TSL2591_GAIN_MED); // Options: LOW, MED, HIGH, MAX
  tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS); // Options: 100MS, 200MS, 300MS, etc.
}

void loop() {
  uint32_t lum = tsl.getFullLuminosity();
  uint16_t ir = lum >> 16;
  uint16_t full = lum & 0xFFFF;
  float lux = tsl.calculateLux(full, ir);

  Serial.print("Full: "); Serial.print(full);
  Serial.print(" | IR: "); Serial.print(ir);
  Serial.print(" | Lux: "); Serial.print(lux, 2);

  // Read and print GY-906 (MLX90614) results
  Serial.print(" | MLX90614 Object: ");
  Serial.print(mlx.readObjectTempC());
  Serial.print(" C, Ambient: ");
  Serial.print(mlx.readAmbientTempC());
  Serial.println(" C");

  delay(1000);
}