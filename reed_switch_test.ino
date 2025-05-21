void setup() {
  Serial.begin(9600);
  pinMode(2, INPUT);
  pinMode(3, INPUT);
}

void loop() {
  int pin2 = digitalRead(2);
  int pin3 = digitalRead(3);

    // Print the state of the reed switches
    // Pins are high when open and low when closed
  Serial.print("Pin 2 C: ");
  Serial.print(pin2);
  Serial.print(" | Pin 3 O: ");
  Serial.println(pin3);

  delay(100); // Wait for 0.1 seconds (100 ms)
}