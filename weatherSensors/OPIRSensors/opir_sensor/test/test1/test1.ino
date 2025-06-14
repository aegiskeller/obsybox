#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_TSL2591.h>

// Create TSL2591 object
Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("TSL2591 Test Harness");

  if (tsl.begin()) {
    Serial.println("TSL2591 found!");
  } else {
    Serial.println("No TSL2591 found ... check your wiring!");
    while (1) delay(10);
  }

  // Optional: Set gain and timing
  tsl.setGain(TSL2591_GAIN_MED);      // Options: LOW, MED, HIGH, MAX
  tsl.setTiming(TSL2591_INTEGRATIONTIME_100MS); // Options: 100MS, 200MS, etc.
}

void loop() {
  float lux = tsl.getLuminosity(TSL2591_VISIBLE);
  float full = tsl.getFullLuminosity();
  float ir = tsl.getLuminosity(TSL2591_INFRARED);

  Serial.print("Visible Lux: "); Serial.println(lux);
  Serial.print("Full Spectrum: "); Serial.println(full);
  Serial.print("Infrared: "); Serial.println(ir);

  delay(2000);
}