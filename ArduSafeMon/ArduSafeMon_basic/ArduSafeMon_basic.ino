//pin 2 is pulled high by pullup resistor
//printing "safe#" to the serial port indicates safe
//printing "notsafe#" to the serial port indicates not safe

bool pinState = LOW;

//-----------------------------------------------------------------------------------------
//--------------------------------------Set safeState--------------------------------------
//-----------------------------------------------------------------------------------------


//-----------------------------------------------------------------------------------------
//-----------------------------------------------------------------------------------------
//-----------------------------------------------------------------------------------------
const int NUM_SAMPLES = 30;
float safeState = 512; // threshold value


void setup() {

  pinMode(A0, INPUT_PULLUP);

  Serial.begin(9600);         // initialize serial
  Serial.flush();             // flush the port
  Serial.print("notsafe#");   // send notsafe# as first state while monitor and client initialize

}

void loop() {
  // Take a sample of readings from A0 and average them
  long sum = 0;
  for (int i = 0; i < NUM_SAMPLES; i++) {
    sum += analogRead(A0);
    delay(5); // small delay between samples
  }
  float avgValue = sum / (float)NUM_SAMPLES;

  // Check against safeState
  bool isSafe = avgValue <= safeState; // safe if avgValue is less than or equal to safeState
  // If avgValue is greater than safeState, it is NOT SAFE

  // Only write to serial if "S#" command is received
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('#');
    if (cmd == "S") {
      if (isSafe) {
        Serial.print("safe#");
      } else {
        Serial.print("notsafe#");
      }
    }
  }

  delay(500); // sample
}
