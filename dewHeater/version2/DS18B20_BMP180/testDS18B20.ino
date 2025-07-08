
#include "OneWire.h"
#include "DallasTemperature.h"
#include <Wire.h>
#include <Adafruit_BMP085.h>

// Define to which pin of the Arduino the 1-Wire bus is connected:
#define ONE_WIRE_BUS 12

// Create a new instance of the oneWire class to communicate with any OneWire device:
OneWire oneWire(ONE_WIRE_BUS);

// Pass the oneWire reference to DallasTemperature library:
DallasTemperature sensors(&oneWire);

// Create a BMP180 object
Adafruit_BMP085 bmp180;

void setup() {
  // Begin serial communication at a baud rate of 9600:
  Serial.begin(9600);
  // Start up the DS18B20 library:
  sensors.begin();

  // Start up the BMP180 sensor:
  Wire.begin();
  if (!bmp180.begin()) {
    Serial.println("Could not find BMP180 sensor! Check wiring.");
  } else {
    Serial.println("BMP180 sensor found.");
  }
}

void loop() {
  // Send the command for all devices on the bus to perform a temperature conversion:
  sensors.requestTemperatures();

  // Fetch the temperature in degrees Celsius for device index:
  float tempC = sensors.getTempCByIndex(0); // the index 0 refers to the first device
  // Fetch the temperature in degrees Fahrenheit for device index:
  float tempF = sensors.getTempFByIndex(0);

  // Print the temperature in Celsius in the Serial Monitor:
  Serial.print("DS18B20 Temperature: ");
  Serial.print(tempC);
  Serial.print(" \xC2\xB0"); // shows degree symbol
  Serial.print("C  |  ");

  // Print the temperature in Fahrenheit
  Serial.print(tempF);
  Serial.print(" \xC2\xB0"); // shows degree symbol
  Serial.println("F");

  // BMP180 readings
  float bmpTemp = bmp180.readTemperature();
  float bmpPressure = bmp180.readPressure() / 100.0; // hPa

  Serial.print("BMP180 Temperature: ");
  Serial.print(bmpTemp);
  Serial.print(" \xC2\xB0C  |  Pressure: ");
  Serial.print(bmpPressure);
  Serial.println(" hPa");

  Serial.println("--------------------------");

  // Wait 1 second:
  delay(1000);
}