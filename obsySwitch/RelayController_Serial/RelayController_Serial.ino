/*
 * ObsyBox Relay Controller - USB Serial Version
 * Arduino Uno with USB Serial communication for ASCOM/NINA integration
 * 
 * This version communicates directly with ASCOM driver via USB Serial
 * Perfect for development and testing without network requirements
 * 
 * Features:
 * - USB Serial command interface
 * - JSON-based communication protocol
 * - EEPROM relay state persistence
 * - Status LED indication
 * - Simple command set for ASCOM integration
 * 
 * Hardware:
 * - Arduino Uno R3
 * - 4-channel relay module (pins 2, 3, 4, 5)
 * - USB connection to PC running NINA/ASCOM
 * 
 * Serial Protocol:
 * Commands (send to Arduino):
 *   GET_STATUS           -> Returns device and relay status
 *   SET_RELAY,1,ON       -> Turn on relay 1 (1-4)
 *   SET_RELAY,1,OFF      -> Turn off relay 1
 *   SET_RELAY,1,TOGGLE   -> Toggle relay 1
 *   GET_RELAY,1          -> Get status of relay 1
 *   EMERGENCY_STOP       -> Turn off all relays
 *   PING                 -> Alive check
 * 
 * Responses (from Arduino):
 *   OK,<data>            -> Success with optional data
 *   ERROR,<message>      -> Error with description
 *   STATUS,<json>        -> Status response
 */

#include <EEPROM.h>

// Relay configuration
const int NUM_RELAYS = 4;
const int relayPins[NUM_RELAYS] = {2, 3, 4, 5};  // Digital pins for relays 1-4
const char* relayNames[NUM_RELAYS] = {"Mount", "Camera", "Focuser", "Aux"};
bool relayStates[NUM_RELAYS] = {false, false, false, false};
bool relayInvert[NUM_RELAYS] = {false, false, false, false};  // TESTING: Changed to active HIGH

// Status LED and timing
const int statusLED = 13;
unsigned long lastHeartbeat = 0;
const unsigned long heartbeatInterval = 2000;  // Heartbeat every 2 seconds
bool ledState = false;

// Communication
String inputCommand = "";
bool commandComplete = false;

// Device info
const char* deviceName = "ObsySwitch-USB";
const char* firmwareVersion = "1.0.0-Serial";
const char* buildDate = __DATE__ " " __TIME__;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.setTimeout(1000);  // 1 second timeout for serial reads
  
  Serial.println(F("# ObsyBox Relay Controller - USB Serial Version"));
  Serial.println(F("# ================================================"));
  Serial.print(F("# Device: "));
  Serial.println(deviceName);
  Serial.print(F("# Firmware: "));
  Serial.println(firmwareVersion);
  Serial.print(F("# Build: "));
  Serial.println(buildDate);
  Serial.println(F("# Commands: GET_STATUS, SET_RELAY,<n>,<state>, GET_RELAY,<n>, PING"));
  Serial.println(F("# Ready for commands..."));
  
  // Initialize relay pins
  for (int i = 0; i < NUM_RELAYS; i++) {
    pinMode(relayPins[i], OUTPUT);
    setRelayState(i, false);  // Start with all relays off
  }
  
  // Initialize status LED
  pinMode(statusLED, OUTPUT);
  digitalWrite(statusLED, LOW);
  
  // Load saved relay states from EEPROM
  loadRelayStatesFromEEPROM();
  
  // Ready indication
  for (int i = 0; i < 5; i++) {
    digitalWrite(statusLED, HIGH);
    delay(100);
    digitalWrite(statusLED, LOW);
    delay(100);
  }
  
  Serial.println(F("OK,READY"));
  printStatus();
}

void loop() {
  // Handle serial commands
  handleSerialInput();
  
  // Process complete commands
  if (commandComplete) {
    processCommand(inputCommand);
    inputCommand = "";
    commandComplete = false;
  }
  
  // Heartbeat LED
  if (millis() - lastHeartbeat >= heartbeatInterval) {
    digitalWrite(statusLED, ledState ? HIGH : LOW);
    ledState = !ledState;
    lastHeartbeat = millis();
  }
  
  delay(10);  // Small delay for stability
}

void handleSerialInput() {
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n' || inChar == '\r') {
      if (inputCommand.length() > 0) {
        commandComplete = true;
      }
    } else {
      inputCommand += inChar;
    }
  }
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();
  
  Serial.print(F("# Processing: "));
  Serial.println(command);
  
  if (command == "PING") {
    Serial.println(F("OK,PONG"));
    
  } else if (command == "GET_STATUS") {
    sendFullStatus();
    
  } else if (command == "EMERGENCY_STOP") {
    for (int i = 0; i < NUM_RELAYS; i++) {
      setRelayState(i, false);
    }
    Serial.println(F("OK,ALL_RELAYS_OFF"));
    
  } else if (command.startsWith("SET_RELAY,")) {
    handleSetRelay(command);
    
  } else if (command.startsWith("GET_RELAY,")) {
    handleGetRelay(command);
    
  } else {
    Serial.print(F("ERROR,UNKNOWN_COMMAND: "));
    Serial.println(command);
  }
}

void handleSetRelay(String command) {
  // Parse command: SET_RELAY,<relay_num>,<state>
  int firstComma = command.indexOf(',');
  int secondComma = command.indexOf(',', firstComma + 1);
  
  if (firstComma == -1 || secondComma == -1) {
    Serial.println(F("ERROR,INVALID_SET_RELAY_FORMAT"));
    return;
  }
  
  int relayNum = command.substring(firstComma + 1, secondComma).toInt();
  String stateStr = command.substring(secondComma + 1);
  
  if (relayNum < 1 || relayNum > NUM_RELAYS) {
    Serial.print(F("ERROR,INVALID_RELAY_NUMBER: "));
    Serial.println(relayNum);
    return;
  }
  
  int relayIndex = relayNum - 1;
  bool newState;
  
  if (stateStr == "ON" || stateStr == "1" || stateStr == "TRUE") {
    newState = true;
  } else if (stateStr == "OFF" || stateStr == "0" || stateStr == "FALSE") {
    newState = false;
  } else if (stateStr == "TOGGLE") {
    newState = !relayStates[relayIndex];
  } else {
    Serial.print(F("ERROR,INVALID_STATE: "));
    Serial.println(stateStr);
    return;
  }
  
  setRelayState(relayIndex, newState);
  
  Serial.print(F("OK,RELAY_"));
  Serial.print(relayNum);
  Serial.print(F("_"));
  Serial.print(relayNames[relayIndex]);
  Serial.print(F("_"));
  Serial.println(newState ? F("ON") : F("OFF"));
}

void handleGetRelay(String command) {
  // Parse command: GET_RELAY,<relay_num>
  int commaIndex = command.indexOf(',');
  
  if (commaIndex == -1) {
    Serial.println(F("ERROR,INVALID_GET_RELAY_FORMAT"));
    return;
  }
  
  int relayNum = command.substring(commaIndex + 1).toInt();
  
  if (relayNum < 1 || relayNum > NUM_RELAYS) {
    Serial.print(F("ERROR,INVALID_RELAY_NUMBER: "));
    Serial.println(relayNum);
    return;
  }
  
  int relayIndex = relayNum - 1;
  
  Serial.print(F("STATUS,{\"relay_id\":"));
  Serial.print(relayNum);
  Serial.print(F(",\"name\":\""));
  Serial.print(relayNames[relayIndex]);
  Serial.print(F("\",\"state\":"));
  Serial.print(relayStates[relayIndex] ? F("true") : F("false"));
  Serial.print(F(",\"pin\":"));
  Serial.print(relayPins[relayIndex]);
  Serial.println(F("}"));
}

void sendFullStatus() {
  Serial.print(F("STATUS,{\"device\":\""));
  Serial.print(deviceName);
  Serial.print(F("\",\"firmware\":\""));
  Serial.print(firmwareVersion);
  Serial.print(F("\",\"uptime\":"));
  Serial.print(millis());
  Serial.print(F(",\"free_memory\":"));
  Serial.print(freeMemory());
  Serial.print(F(",\"relays\":["));
  
  for (int i = 0; i < NUM_RELAYS; i++) {
    if (i > 0) Serial.print(F(","));
    Serial.print(F("{\"id\":"));
    Serial.print(i + 1);
    Serial.print(F(",\"name\":\""));
    Serial.print(relayNames[i]);
    Serial.print(F("\",\"state\":"));
    Serial.print(relayStates[i] ? F("true") : F("false"));
    Serial.print(F(",\"pin\":"));
    Serial.print(relayPins[i]);
    Serial.print(F("}"));
  }
  
  Serial.println(F("]}"));
}

void setRelayState(int relayIndex, bool state) {
  if (relayIndex < 0 || relayIndex >= NUM_RELAYS) return;
  
  relayStates[relayIndex] = state;
  
  // Apply inversion for active-low relay modules
  bool outputState = relayInvert[relayIndex] ? !state : state;
  digitalWrite(relayPins[relayIndex], outputState ? HIGH : LOW);
  
  Serial.print(F("# Relay "));
  Serial.print(relayIndex + 1);
  Serial.print(F(" ("));
  Serial.print(relayNames[relayIndex]);
  Serial.print(F("): "));
  Serial.println(state ? F("ON") : F("OFF"));
  
  // Save state to EEPROM
  EEPROM.write(relayIndex, state ? 1 : 0);
  
  // Brief LED flash to indicate activity
  digitalWrite(statusLED, HIGH);
  delay(50);
  digitalWrite(statusLED, LOW);
}

void loadRelayStatesFromEEPROM() {
  Serial.println(F("# Loading relay states from EEPROM..."));
  for (int i = 0; i < NUM_RELAYS; i++) {
    byte savedState = EEPROM.read(i);
    if (savedState == 0 || savedState == 1) {
      setRelayState(i, savedState == 1);
    } else {
      setRelayState(i, false);  // Default to off if invalid data
    }
  }
}

void printStatus() {
  Serial.println(F("# === Current Status ==="));
  Serial.print(F("# Free RAM: "));
  Serial.print(freeMemory());
  Serial.println(F(" bytes"));
  
  for (int i = 0; i < NUM_RELAYS; i++) {
    Serial.print(F("# Relay "));
    Serial.print(i + 1);
    Serial.print(F(" ("));
    Serial.print(relayNames[i]);
    Serial.print(F("): "));
    Serial.println(relayStates[i] ? F("ON") : F("OFF"));
  }
  Serial.println(F("# ======================"));
}

int freeMemory() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}