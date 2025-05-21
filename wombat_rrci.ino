#include <Arduino.h>

String serialin; //incoming serial data
String str; //store the state  of opened/closed/safe pins
String cmdmode; //store the latest command until completed

// Motor A connections
int enA = 9;
int in1 = 8;
int in2 = 7;
// Motor B connections
int enB = 10;
int in3 = 6;
int in4 = 5;

//input sensors
#define opened 3  // roof open sensor
#define closed 2  // roof closed sensor

int led = 10; // the pin the scope safe LED is connected to

unsigned  long end_time;
bool lost = false; //roof not reporting state

void setup()  {
end_time=millis()+60000; //roof lost reset timer ~60 seconds  change to suit  your rquirments to determine if roof is lost

  //Begin Serial Comunication(configured  for 9600baud)
  Serial.begin(9600);
	// Set all the motor control pins to outputs
	pinMode(enA, OUTPUT);
	pinMode(enB, OUTPUT);
	pinMode(in1, OUTPUT);
	pinMode(in2, OUTPUT);
	pinMode(in3, OUTPUT);
	pinMode(in4, OUTPUT);
	
	// Turn off motors - Initial state
	digitalWrite(in1, LOW);
	digitalWrite(in2, LOW);
	digitalWrite(in3, LOW);
	digitalWrite(in4, LOW);

  //enable the motors
  analogWrite(enA, 255);
	analogWrite(enB, 255);

  //pins as INPUT
  pinMode(closed, INPUT_PULLUP);
  pinMode(opened,  INPUT_PULLUP); 

  // set cmd mode to ""
  cmdmode = "";
    
  Serial.write("RRCI#"); //init string
   
}

void loop() {
  Timer();
  
  //Verify connection by serial
  while (Serial.available()>0) {
    //Read  Serial data and allocate on serialin
 
    serialin = Serial.readStringUntil('#');

    Serial.print("I received: ");
    Serial.println(serialin);
     
    if (serialin == "open"){ 
      Serial.println("opening - set motors on");
      // Perform a slow start by ramping up the speed
      // do this by incrementing the PWM value
	    digitalWrite(in1, LOW);
	    digitalWrite(in2, HIGH);
	    digitalWrite(in3, LOW);
	    digitalWrite(in4, HIGH);
      cmdmode = "opening";
      for (int speed = 0; speed <= 255; speed += 5) {
        analogWrite(enA, speed);
        analogWrite(enB, speed);
        delay(50); // wait for 50ms
      }
    }
   
    else if (serialin == "close"){
      Serial.println("closing - set motors on");
      // Perform a slow start by ramping up the speed
      // do this by incrementing the PWM value
      digitalWrite(in1, HIGH);
      digitalWrite(in2, LOW);
      digitalWrite(in3, HIGH);
      digitalWrite(in4, LOW);
      cmdmode = "closing";
      for (int speed = 0; speed <= 255; speed += 5) {
        analogWrite(enA, speed);
        analogWrite(enB, speed);
        delay(50); // wait for 50ms
      }
    }

    else if (serialin == "stop"){
      digitalWrite(in1, LOW);
  	  digitalWrite(in2, LOW);
  	  digitalWrite(in3, LOW);
	    digitalWrite(in4, LOW);
      cmdmode = "stopped";
    }
  }  

  if (cmdmode == "closing" && digitalRead(closed) == LOW) { //stop motors when 'closed' reached
    digitalWrite(in1, LOW);
	  digitalWrite(in2, LOW);
	  digitalWrite(in3, LOW);
	  digitalWrite(in4, LOW);
    cmdmode = ""; // end of cmd to close
  }
  if (cmdmode == "opening" && digitalRead(opened) == LOW) {  //stop motors when 'opened' reached
   	digitalWrite(in1, LOW);
	  digitalWrite(in2, LOW);
  	digitalWrite(in3, LOW);
	  digitalWrite(in4, LOW);
    cmdmode = ""; // end of cmd to open
  }
  if (serialin  == "Parkstatus"){ // exteranl query command to fetch RRCI data
    Serial.println("0#");
    serialin = ""; 
  }
 
  if (serialin == "get"){ // exteranl query  command to fetch RRCI data
  
    if (digitalRead(opened) == LOW){
      str += "opened,"; 
          
    }
    else if (digitalRead(closed) == LOW){
      str += "closed,";
    }
    
    if ((digitalRead(closed) == HIGH) && (digitalRead(opened) == HIGH)){
        str += "unknown,";
    }

    if ((digitalRead(closed) == HIGH)  && (digitalRead(opened) == LOW) && (lost == false)){
      str += "not_moving_o#";
      end_time=millis()+60000; //reset the timer
    }
    
    if ((digitalRead(closed)  == LOW) && (digitalRead(opened) == HIGH) && (lost == false)){
      str += "not_moving_c#";
      end_time=millis()+60000; //reset the timer
    }
    if ((digitalRead(closed)  == HIGH) && (digitalRead(opened) == HIGH) && (lost == false)){
        str +=  "moving#";
        
    }     
    else if ((digitalRead(closed) == HIGH)  && (digitalRead(opened) == HIGH) && (lost == true)){   
        str += "unknown#";
    }
    if (str.endsWith(","))  {
      str += "unknown#";
    }
  
    Serial.println(str);  //send serial data
    serialin = "";  
    str = "";
    //delay(100);
  } // end get

  if (serialin == "Status"){
  Serial.println("RoofOpen#");
  
  }
  serialin  = "";  
  //str = "";
} 
   
void Timer(){ // detect roof lost
  if(millis()>=end_time){
     //60 s have passed!!
      if ((digitalRead(closed)  == HIGH) && (digitalRead(opened)) == HIGH){
       lost = true; //where the heck  is the roof position?
     }
     
             
  } 
    if ((digitalRead(closed)  == LOW) or (digitalRead(opened)) == LOW){
             lost = false; //roof state  is known
             end_time=millis()+60000; //reset the timer  
  }
  
}