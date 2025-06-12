// here the main board of the dew heater is the Arduino Uno
// and it is the slave to the lolin master 
// the arduino sends the data to the lolin and then
// the Lolin sends it to the iot Cloud
#define MOSFETPIN 3 //n-channel- PWM capable
#define THERMPIN A0  //10k thermistor and 10k resistor

#include "DHT.h"
#include <string.h>
#include <stdlib.h>
#include <Wire.h>

#define DHTpin 10 
#define DHTTYPE DHT11
#define NUMSAMPLES 10            // how many samples to average in order to smooth reading

DHT dht(DHTpin,DHTTYPE);


//#include <avr/pgmspace.h>
// Big lookup Table (approx 750 entries), subtract 238 from ADC reading to start at 0*C. Entries in 10ths of degree i.e. 242 = 24.2*C Covers 0*C to 150*C For 10k resistor/10k thermistor voltage divider w/ therm on the + side.
const int temps[] PROGMEM = {0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 143, 144, 145, 146, 147, 148, 149, 150, 151, 151, 152, 153, 154, 155, 156, 157, 158, 159, 159, 160, 161, 162, 163, 164, 165, 166, 167, 167, 168, 169, 170, 171, 172, 173, 174, 175, 175, 176, 177, 178, 179, 180, 181, 182, 182, 183, 184, 185, 186, 187, 188, 189, 190, 190, 191, 192, 193, 194, 195, 196, 197, 197, 198, 199, 200, 201, 202, 203, 204, 205, 205, 206, 207, 208, 209, 210, 211, 212, 212, 213, 214, 215, 216, 217, 218, 219, 220, 220, 221, 222, 223, 224, 225, 226, 227, 228, 228, 229, 230, 231, 232, 233, 234, 235, 235, 236, 237, 238, 239, 240, 241, 242, 243, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 252, 253, 254, 255, 256, 257, 258, 259, 260, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 422, 423, 424, 425, 426, 427, 428, 429, 430, 432, 433, 434, 435, 436, 437, 438, 439, 441, 442, 443, 444, 445, 446, 448, 449, 450, 451, 452, 453, 455, 456, 457, 458, 459, 460, 462, 463, 464, 465, 466, 468, 469, 470, 471, 472, 474, 475, 476, 477, 479, 480, 481, 482, 484, 485, 486, 487, 489, 490, 491, 492, 494, 495, 496, 498, 499, 500, 501, 503, 504, 505, 507, 508, 509, 511, 512, 513, 515, 516, 517, 519, 520, 521, 523, 524, 525, 527, 528, 530, 531, 532, 534, 535, 537, 538, 539, 541, 542, 544, 545, 547, 548, 550, 551, 552, 554, 555, 557, 558, 560, 561, 563, 564, 566, 567, 569, 570, 572, 574, 575, 577, 578, 580, 581, 583, 585, 586, 588, 589, 591, 593, 594, 596, 598, 599, 601, 603, 604, 606, 608, 609, 611, 613, 614, 616, 618, 620, 621, 623, 625, 627, 628, 630, 632, 634, 636, 638, 639, 641, 643, 645, 647, 649, 651, 653, 654, 656, 658, 660, 662, 664, 666, 668, 670, 672, 674, 676, 678, 680, 683, 685, 687, 689, 691, 693, 695, 697, 700, 702, 704, 706, 708, 711, 713, 715, 718, 720, 722, 725, 727, 729, 732, 734, 737, 739, 741, 744, 746, 749, 752, 754, 757, 759, 762, 764, 767, 770, 773, 775, 778, 781, 784, 786, 789, 792, 795, 798, 801, 804, 807, 810, 813, 816, 819, 822, 825, 829, 832, 835, 838, 842, 845, 848, 852, 855, 859, 862, 866, 869, 873, 877, 881, 884, 888, 892, 896, 900, 904, 908, 912, 916, 920, 925, 929, 933, 938, 942, 947, 952, 956, 961, 966, 971, 976, 981, 986, 991, 997, 1002, 1007, 1013, 1019, 1024, 1030, 1036, 1042, 1049, 1055, 1061, 1068, 1075, 1082, 1088, 1096, 1103, 1110, 1118, 1126, 1134, 1142, 1150, 1159, 1168, 1177, 1186, 1196, 1206, 1216, 1226, 1237, 1248, 1260, 1272, 1284, 1297, 1310, 1324, 1338, 1353, 1369, 1385, 1402, 1420, 1439, 1459, 1480, 1502};


byte DHTdat[5];              //data from DHT11 sensor to be stored in 0.1 humidity% 2.3 degrees C
float tempoffset = 5.0;          //setpoint offset 
char offsetmode = "A";       //default offset
int ambtemp, ambhum, dptemp; // all measured in 1/10's
int pwmoutputdefault = 52;   // 10%
int16_t val = 0;             // the 2 byte value we are going to send over i2c
int samples[NUMSAMPLES];
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
}

void loop()
{
  int teletemp;       //telescope temperature
  int thermerror = 0; // flag for thermistor error
  uint8_t i;
  float averagett;

  for (i=0; i< NUMSAMPLES; i++) {
    samples[i] = analogRead(THERMPIN);
    delay(100);
  }

  //average the samples
  averagett = 0;
  for (i=0; i< NUMSAMPLES; i++) {
     averagett += samples[i];
  }
  averagett /= NUMSAMPLES;
  teletemp = (int)averagett;

  //Serial.println(teletemp);
  if ((teletemp == 0) | (teletemp > 950))
  {
    thermerror = thermerror | 1;
  } //thermistor error detected
  teletemp = teletemp - 238;
  if (teletemp < 0)
  {
    teletemp = 0;
  } //lookup table won't work if index<0
  teletemp = pgm_read_word(&temps[teletemp]);
  //Serial.println(teletemp);
  int ambtemp = dht.readTemperature() * 10;
  int ambhum = dht.readHumidity() * 10;
  dptemp = ambtemp - ((1000-ambhum)/5);

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
  Serial.print(F(" Mode: "));
  Serial.println(offsetmode);

  if (isnan(ambtemp) || isnan(ambhum))
  {
    thermerror = thermerror | 2;
  }

  int temptarget;
  if (strcmp(offsetmode, "D") == 0)
  {
    temptarget = dptemp + tempoffset * 10;
  }
  else
  {
    temptarget = ambtemp + tempoffset * 10; //default to (higher) ambient temp if anything but 'D'
  }

  int pwmoutput;
  pwmoutput = constrain(map(temptarget - teletemp, -10, 10, 0, 255), 0, 255);
  if (thermerror)
  {
    pwmoutput = pwmoutputdefault;
  }
 // if (teletemp < 5) { // this is here while I sort out a more robust thermoresistor
//    pwmoutput=250; // set the power to max
//  }
  analogWrite(MOSFETPIN, pwmoutput);

  pwmoutput = (pwmoutput * 39) / 100; //scale to %
  //Serial.print(F(" HTR: "));
  //Serial.print(pwmoutput);
  //Serial.print(F("%"));
  //Serial.println();
  // now we can package the data to a string and then pass it via i2c
  float at = ((float)ambtemp)/10; //converts the float or integer to a string. 
  //(floatVar, minStringWidthIncDecimalPoint, numVarsAfterDecimal, empty array);
  dtostrf(at, 4, 1, sat);
  float ah = ((float)ambhum)/10;
  dtostrf(ah, 4, 1, sah);
  float tt = ((float)teletemp)/10;
  dtostrf(tt, 4, 1, stt);
  float dp = ((float)dptemp/10);
  //Serial.println(dp);
  dtostrf(dp, 4, 1, sdp);
  //Serial.println(sdp);

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
  Serial.println(dataPacket);


  // write out the message from the master
  Serial.print("mastermsg: ");
  Serial.println(masterMsg);
  // Interpret the message from the master
  String mstr_dt = getValue(masterMsg, ';', 0);
  String mstr_mode = getValue(masterMsg, ';', 1);
  char * end;
  // assign the new values 
  tempoffset = strtod(mstr_dt.c_str(), &end);
  // we have a problem here - string and chars issue
  // possible workaround is to use int message from master and
  // then translate to the A or D
  //Serial.print("after master read: ");
  //Serial.println(mstr_mode);
  if (mstr_mode == "A" or mstr_mode == "D") {
    strcpy(offsetmode, mstr_mode.c_str());
    tempoffset = strtod(mstr_dt.c_str(), NULL);
  }
  else {
    Serial.println("not a valid mode");
    offsetmode = 'A';
    tempoffset = 5.0;
  }
  //Serial.println(offsetmode);
  //offsetmode = mstr_mode.c_str();
  delay(3000);
}

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
  // we send a 2 byte array
  // https://thewanderingengineer.com/2015/05/06/sending-16-bit-and-32-bit-numbers-with-arduino-i2c/
  // byte valarray[2];
  // valarray[0] = (val >> 8) & 0xFF;
  // valarray[1] = val & 0xFF;
  // Wire.write(valarray, 2);  /*send data on request*/
  Wire.write(dataPacket);
}