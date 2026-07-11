/*
 * Arduino_Firmware.ino
 * Modified for ESP8266 (e.g., LOLIN/Wemos D1 mini)
 * and then for Ard Uno
 */

#include <Servo.h>

constexpr auto DEVICE_GUID = "b45ba2c9-f554-4b42-a43c-10605cb3b84d";

constexpr auto COMMAND_PING = "COMMAND:PING";
constexpr auto RESULT_PING = "RESULT:PING:OK:";

constexpr auto COMMAND_INFO = "COMMAND:INFO";
constexpr auto RESULT_INFO = "RESULT:Telescope Dust Cover Firmware v1.0";

constexpr auto COMMAND_GETSTATE = "COMMAND:GETSTATE";
constexpr auto RESULT_STATE_UNKNOWN = "RESULT:STATE:UNKNOWN";
constexpr auto RESULT_STATE_OPEN = "RESULT:STATE:OPEN";
constexpr auto RESULT_STATE_CLOSED = "RESULT:STATE:CLOSED";

constexpr auto COMMAND_OPEN = "COMMAND:OPEN";
constexpr auto COMMAND_CLOSE = "COMMAND:CLOSE";

constexpr auto ERROR_INVALID_COMMAND = "ERROR:INVALID_COMMAND";

enum CoverState {
    unknown,
    open,
    closed
} state;

Servo servo;

// Use D7 for servo signal on LOLIN/Wemos D1 mini
const int SERVO_PIN = 7;
const int OPEN_LIMIT_SWITCH_PIN = 9;
const int CLOSE_LIMIT_SWITCH_PIN = 8;

void updateStateFromLimitSwitches();

// The `setup` function runs once when you press reset or power the board.
void setup() {
    state = unknown;

    // Initialize serial port I/O.
    Serial.begin(9600); // 115200 is typical for ESP8266
    while (!Serial) {
        ; // Wait for serial port to connect (optional on ESP8266)
    }
    delay(100); // Give serial time to initialize

    Serial.println("Dust Cover Firmware starting...");
    Serial.print("Servo pin: "); Serial.println(SERVO_PIN);
    Serial.println("Attaching servo...");
    servo.attach(SERVO_PIN, 450, 2020); // Wider pulse range for full rotation
    Serial.println("Servo attached. Position unchanged until command.");

    // Limit switches are assumed to pull LOW when pressed.
    pinMode(OPEN_LIMIT_SWITCH_PIN, INPUT_PULLUP);
    pinMode(CLOSE_LIMIT_SWITCH_PIN, INPUT_PULLUP);
    updateStateFromLimitSwitches();

    // Optionally turn off built-in LED
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, HIGH); // Off for active-low LED on ESP8266
    Serial.println("Setup complete.");
}

// The `loop` function runs over and over again until power down or reset.
void loop() {
    updateStateFromLimitSwitches();

    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim(); // Remove any \r or whitespace
        Serial.print("Received command: ");
        Serial.println(command);
        if (command == COMMAND_PING) {
            handlePing();
        }
        else if (command == COMMAND_INFO) {
            sendFirmwareInfo();
        }
        else if (command == COMMAND_GETSTATE) {
            sendCurrentState();
        }
        else if (command == COMMAND_OPEN) {
            Serial.println("Opening cover...");
            openCover();
        }
        else if (command == COMMAND_CLOSE) {
            Serial.println("Closing cover...");
            closeCover();
        }
        else {
            Serial.println("Invalid command received.");
            handleInvalidCommand();
        }
    }
}

void handlePing() {
    Serial.println("Handling PING command.");
    Serial.print(RESULT_PING);
    Serial.println(DEVICE_GUID);
}

void sendFirmwareInfo() {
    Serial.println("Sending firmware info.");
    Serial.println(RESULT_INFO);
}

void sendCurrentState() {
    updateStateFromLimitSwitches();

    Serial.print("Reporting current state: ");
    switch (state) {
    case open:
        Serial.println("OPEN");
        Serial.println(RESULT_STATE_OPEN);
        break;
    case closed:
        Serial.println("CLOSED");
        Serial.println(RESULT_STATE_CLOSED);
        break;
    default:
        Serial.println("UNKNOWN");
        Serial.println(RESULT_STATE_UNKNOWN);
        break;
    }
}

void updateStateFromLimitSwitches() {
    bool openLimitPressed = digitalRead(OPEN_LIMIT_SWITCH_PIN) == LOW;
    bool closeLimitPressed = digitalRead(CLOSE_LIMIT_SWITCH_PIN) == LOW;

    if (openLimitPressed && !closeLimitPressed) {
        state = open;
    }
    else if (closeLimitPressed && !openLimitPressed) {
        state = closed;
    }
    else {
        state = unknown;
    }
}

void openCover() {
    int pos = servo.read();
    Serial.print("Current position of servo is ");
    Serial.println(pos);
    if (pos < 180) {
        for (; pos <= 180; pos++) {
            if (digitalRead(OPEN_LIMIT_SWITCH_PIN) == LOW) {
                Serial.println("Open limit reached. Stopping servo.");
                break;
            }
            servo.write(pos);
            if (pos % 10 == 0) {
                Serial.print("Moving servo to: ");
                Serial.println(pos);
            }
            delay(15); // ESP8266 is fast, so use a shorter delay for smoothness
            yield();
        }
    }
    updateStateFromLimitSwitches();
    Serial.println("Open command complete.");
}

void closeCover() {
    int pos = servo.read();
    Serial.print("Current position of servo is ");
    Serial.println(pos);
    if (pos > 0) {
        for (; pos >= 0; pos--) {
            if (digitalRead(CLOSE_LIMIT_SWITCH_PIN) == LOW) {
                Serial.println("Close limit reached. Stopping servo.");
                break;
            }
            servo.write(pos);
            if (pos % 10 == 0) {
                Serial.print("Moving servo to: ");
                Serial.println(pos);
            }
            delay(15);
            yield();
        }
    }
    updateStateFromLimitSwitches();
    Serial.println("Close command complete.");
}

void handleInvalidCommand() {
    Serial.println("Sending invalid command error.");
    Serial.println(ERROR_INVALID_COMMAND);
}