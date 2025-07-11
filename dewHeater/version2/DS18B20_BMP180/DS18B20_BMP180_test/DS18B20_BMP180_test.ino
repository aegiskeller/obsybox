#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <OneWire.h>
#include <DallasTemperature.h>

Adafruit_BMP085 bmp;

// DS18B20 setup
#define ONE_WIRE_BUS 4  // Connect DS18B20 data to D2 (GPIO4)
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

void setup() 
{
  Serial.begin(9600);
  sensors.begin();
  Wire.begin(2, 14); // SDA = D2, SCL = D14 for your board
  if (!bmp.begin()) 
  {
    Serial.println("Could not find BMP180 or BMP085 sensor at 0x77");
    while (1) { yield(); }
  }
}

void loop() 
{
  // DS18B20 reading
  sensors.requestTemperatures();
  float dsTemp = sensors.getTempCByIndex(0);

  delay(20); // Add a small delay before I2C access

  // BMP180 readings
  float bmpTemp = bmp.readTemperature();
  float bmpPressure = bmp.readPressure();

  Serial.print("DS18B20 Temperature = ");
  Serial.print(dsTemp);
  Serial.println(" Celsius");

  Serial.print("BMP180 Temperature = ");
  Serial.print(bmpTemp);
  Serial.println(" Celsius");

  Serial.print("BMP180 Pressure = ");
  Serial.print(bmpPressure);
  Serial.println(" Pascal");

  Serial.println();
  delay(5000);
}