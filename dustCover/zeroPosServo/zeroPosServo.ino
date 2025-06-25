#include <Servo.h>
Servo servo;
void setup() {
  servo.attach(D7, 500, 2500);
  servo.write(0); // Move to 0 degrees
}
void loop() {}