#include <DHT.h>

#define DHTPIN 4         // DHT22 data pin connected to GPIO 4
#define DHTTYPE DHT22    // DHT 22 (AM2302)
#define ANEMOMETER_PIN A0 // Anemometer connected to ADC (A0)

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
}

void loop() {
  // Read DHT22
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // Read Anemometer (analog value)
  int anemometerValue = analogRead(ANEMOMETER_PIN);

  // Print results
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print(" °C, Humidity: ");
  Serial.print(humidity);
  Serial.print(" %, Anemometer ADC: ");
  Serial.println(anemometerValue);

  delay(2000); // Wait 2 seconds between readings
}