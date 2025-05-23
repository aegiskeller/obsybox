// from https://www.cloudynights.com/topic/792701-arduino-based-rg-11-safety-monitor-for-nina-64bit/


//pin 2 is pulled high by pullup resistor
//printing "safe#" to the serial port indicates safe
//printing "notsafe#" to the serial port indicates not safe

bool pinState = LOW;

//-----------------------------------------------------------------------------------------
//--------------------------------------Set safeState--------------------------------------
//-----------------------------------------------------------------------------------------

bool safeState = LOW; //set desired safeState of the monitor HIGH or LOW

//-----------------------------------------------------------------------------------------
//-----------------------------------------------------------------------------------------
//-----------------------------------------------------------------------------------------

void setup() {

  pinMode(2, INPUT);

  Serial.begin(9600);         // initialize serial
  Serial.flush();             // flush the port
  Serial.print("notsafe#");   // send notsafe# as first state while monitor and client initialize

}

void loop() {

  String cmd;

  if (Serial.available() > 0) {
    cmd = Serial.readStringUntil('#');
    if (cmd == "S") {
      pinState = digitalRead(2);
      if (pinState == safeState) {
        Serial.print("safe#");
      }
      if (pinState != safeState) {
        Serial.print("notsafe#");
      }

    }

  }
}
