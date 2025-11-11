/*
 * Simple Relay Test - Direct Pin Control
 * 
 * This sketch directly controls pin 2 to test relay switching
 * without any complex logic. Use this to verify basic functionality.
 */

const int RELAY_PIN = 2;
const int LED_PIN = 13;

void setup() {
  Serial.begin(9600);
  Serial.println("=== SIMPLE RELAY TEST ===");
  Serial.println("Pin 2 will switch HIGH/LOW every 2 seconds");
  Serial.println("Listen for relay clicks...");
  Serial.println("Commands: 'h' = HIGH, 'l' = LOW, 's' = status");
  
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  
  // Start with relay off
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
  
  Serial.println("Ready! Pin 2 = LOW");
}

void loop() {
  static unsigned long lastToggle = 0;
  static bool pinState = false;
  
  // Auto-toggle every 3 seconds for testing
  if (millis() - lastToggle > 3000) {
    pinState = !pinState;
    digitalWrite(RELAY_PIN, pinState ? HIGH : LOW);
    digitalWrite(LED_PIN, pinState);  // Mirror on built-in LED
    
    Serial.print("Pin 2 = ");
    Serial.println(pinState ? "HIGH" : "LOW");
    Serial.println("(Listen for relay click!)");
    
    lastToggle = millis();
  }
  
  // Check for serial commands
  if (Serial.available()) {
    char cmd = Serial.read();
    
    switch (cmd) {
      case 'h':
      case 'H':
        digitalWrite(RELAY_PIN, HIGH);
        digitalWrite(LED_PIN, HIGH);
        Serial.println("Pin 2 = HIGH");
        break;
        
      case 'l':
      case 'L':
        digitalWrite(RELAY_PIN, LOW);
        digitalWrite(LED_PIN, LOW);
        Serial.println("Pin 2 = LOW");
        break;
        
      case 's':
      case 'S':
        Serial.print("Pin 2 = ");
        Serial.println(digitalRead(RELAY_PIN) ? "HIGH" : "LOW");
        Serial.print("LED 13 = ");
        Serial.println(digitalRead(LED_PIN) ? "HIGH" : "LOW");
        break;
    }
  }
}