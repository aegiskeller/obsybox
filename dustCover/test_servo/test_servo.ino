/*
 * This ESP8266 NodeMCU code was developed by newbiely.com
 *
 * This ESP8266 NodeMCU code is made available for public use without any restriction
 *
 * For comprehensive instructions and wiring diagrams, please visit:
 * https://newbiely.com/tutorials/esp8266/esp8266-servo-motor
 */

#include <Servo.h>

Servo servo;  // create servo object to control a servo

int pos = 0;    // variable to store the servo position

void setup() {
  servo.attach(D7, 500, 2700);  // attaches the servo on pin D4 to the servo object
}

void loop() {
  // Move from 0 to 180 with ease-in/ease-out
  for (pos = 5; pos <= 180; pos++) {
    servo.write(pos);
    // Ease-in/ease-out: delay is largest at start/end, smallest in the middle
    float progress = (float)pos / 180.0;
    int d = 300 * pow((progress - 0.5), 2) + 5; // Parabolic: 30ms at ends, 5ms in middle
    delay(d);
  }

  // Move from 180 to 0 with ease-in/ease-out
  for (pos = 180; pos >= 5; pos--) {
    servo.write(pos);
    float progress = (float)pos / 180.0;
    int d = 300 * pow((progress - 0.5), 2) + 5;
    delay(d);
  }
}
