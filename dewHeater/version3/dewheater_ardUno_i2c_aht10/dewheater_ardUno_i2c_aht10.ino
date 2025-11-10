// here the main board of the dew heater is the Arduino Uno
// and it is the slave to the lolin master 
// the arduino sends the data to the lolin and then
// the Lolin sends it to the iot Cloud
#define MOSFETPIN 3 //n-channel- PWM capable
#define DS18B20_PIN 2

#include "DHT.h"
#include <string.h>
#include <stdlib.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define DHTpin 10 
#define DHTTYPE DHT11

DHT dht(DHTpin,DHTTYPE);
Adafruit_AHTX0 aht10;
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);

byte DHTdat[5];              //data from DHT11 sensor to be stored in 0.1 humidity% 2.3 degrees C
float tempoffset = 5.0;          //setpoint offset 
char offsetmode = 'A'; // use single quotes for char       //default offset
int ambtemp, ambhum, dptemp; // all measured in 1/10's
int pwmoutputdefault = 52;   // 10%
int16_t val = 0;             // the 2 byte value we are going to send over i2c
char masterMsg[12]={};
char sat[10];                // empty array for the number string we send to the master
char sah[10];
char stt[10];
char sdp[10];
char sdlt[10];
char sht[10];
char dataPacket[35];

String getValue(String data, char separator, int index)
{
  int found = 0;
  int strIndex[] = {0, -1};
  int maxIndex = data.length()-1;

  for(int i=0; i<=maxIndex && found<=index; i++){
    if(data.charAt(i)==separator || i==maxIndex){
        found++;
        strIndex[0] = strIndex[1]+1;
        strIndex[1] = (i == maxIndex) ? i+1 : i;
    }
  }

  return found>index ? data.substring(strIndex[0], strIndex[1]) : "";
}

void setup()
{
  Serial.begin(9600); //if needed for debugging
  dht.begin();
  Wire.begin(0x08);
  Wire.onReceive(receiveEvent); /* register receive event */
  Wire.onRequest(requestEvent); /* register request event */
  delay(500);      //and wait a bit for conversion to finish

  // Initialize AHT10
  if (!aht10.begin()) {
    Serial.println("Could not find AHT10 sensor! Check wiring.");
  } else {
    Serial.println("AHT10 sensor found.");
  }
  ds18b20.begin();
}

void loop()
{
  int thermerror = 0; // flag for thermistor error

  // --- DS18B20 as teletemp ---
  ds18b20.requestTemperatures();
  float ds18b20_temp = ds18b20.getTempCByIndex(0);
  int teletemp = ds18b20_temp * 10; // tenths of a degree


  // --- AHT10 readings ---
  sensors_event_t humidity, temp;
  aht10.getEvent(&humidity, &temp);

  int ambtemp = temp.temperature * 10; // Now using AHT10 for temperature
  int ambhum = humidity.relative_humidity * 10; // Using AHT10 for humidity
  dptemp = ambtemp - ((1000-ambhum)/5);

  if (ds18b20_temp == DEVICE_DISCONNECTED_C) {
    Serial.println("DS18B20 not found, using AMB for teletemp");
    teletemp = ambtemp;
    thermerror = thermerror | 1;
  }

  if (isnan(ambtemp) || isnan(ambhum))
  {
    thermerror = thermerror | 2;
  }

  int temptarget;
  if (offsetmode == 'D') {
    temptarget = dptemp + tempoffset * 10;
  } else {
    temptarget = ambtemp + tempoffset * 10;
  }

  int pwmoutput;
  pwmoutput = constrain(map(temptarget - teletemp, -10, 10, 0, 255), 0, 255);
  if (thermerror)
  {
    pwmoutput = pwmoutputdefault;
  }
  if (teletemp < 5) { // this is here while I sort out a more robust thermoresistor
    pwmoutput=255; // set the power to max
  }
  analogWrite(MOSFETPIN, pwmoutput);

  pwmoutput = (pwmoutput * 39) / 100; //scale to %

  // Print status line with all sensor readings and heater percentage
  Serial.print(F("Hmdty: "));
  Serial.print((float)ambhum/10);
  Serial.print(F("%  AT: "));
  Serial.print((float)ambtemp/10);
  Serial.print(F("  TT: "));
  Serial.print((float)teletemp/10);
  Serial.print(F("  DP: "));
  Serial.print((float)dptemp/10);
  Serial.print(F("  DelT: "));
  Serial.print(tempoffset);
  Serial.print(F("  HEATR: "));
  Serial.print(pwmoutput);
  Serial.print(F("%  Mode: "));
  Serial.println(offsetmode);

  // now we can package the data to a string and then pass it via i2c
  float at = ((float)ambtemp)/10; //converts the float or integer to a string. 
  dtostrf(at, 4, 1, sat);
  float ah = ((float)ambhum)/10;
  dtostrf(ah, 4, 1, sah);
  float tt = ((float)teletemp)/10;
  dtostrf(tt, 4, 1, stt);
  float dp = ((float)dptemp/10);
  dtostrf(dp, 4, 1, sdp);

  float dlt = tempoffset;
  dtostrf(dlt, 4, 1, sdlt);
  float ht = pwmoutput;
  dtostrf(ht, 3, 0, sht);
  strcpy(dataPacket, sat);
  strcat(dataPacket, ";");
  strcat(dataPacket, sah);
  strcat(dataPacket, ";");
  strcat(dataPacket, stt);
  strcat(dataPacket, ";");
  strcat(dataPacket, sdlt);
  strcat(dataPacket, ";");
  strcat(dataPacket, sht);
  strcat(dataPacket, ";");
  strcat(dataPacket, sdp);

  // write out the message from the master
  Serial.print("mastermsg: ");
  Serial.println(masterMsg);
  // Interpret the message from the master
  String mstr_dt = getValue(masterMsg, ';', 0);
  String mstr_mode = getValue(masterMsg, ';', 1);
  char * end;
  // assign the new values 
  tempoffset = strtod(mstr_dt.c_str(), &end);
  if (mstr_mode == "A" or mstr_mode == "D") {
    strcpy(&offsetmode, mstr_mode.c_str());
    tempoffset = strtod(mstr_dt.c_str(), NULL);
  }
  else {
    Serial.println("not a valid mode");
    offsetmode = 'A';
    tempoffset = 5.0;
  }
  delay(3000);
}`
// function that executes whenever data is received from master
void receiveEvent(int howMany) {
 int i=0;
 while (0 <Wire.available()) {
    masterMsg[i] = Wire.read();      /* receive byte as a character */
    i=i+1;
    yield();
  }
}

// function that executes whenever data is requested from master
void requestEvent() {
  Wire.write(dataPacket);
}