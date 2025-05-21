String serialin; //incoming serial data
String str; //store the state  of opened/closed/safe pins

//relays
#define stop 4
#define sensor 5
#define close 6
#define open 7

//input sensors
#define opened 11  // roof open  sensor
#define closed 12  // roof closed sensor
#define safe 13   // scope  safety sensor

int led = 10; // the pin the scope safe LED is connected to

unsigned  long end_time;
bool lost = false; //roof not reporting state

void setup()  {
end_time=millis()+60000; //roof lost reset timer ~60 seconds  change to suit  your rquirments to determine if roof is lost

  //Begin Serial Comunication(configured  for 9600baud)
  Serial.begin(9600);
  //pin relay as OUTPUT
  pinMode(open,  OUTPUT); 
  pinMode(close, OUTPUT);
  pinMode(stop, OUTPUT);
  pinMode(sensor,  OUTPUT);
  
  //pins as INPUT
  pinMode(closed, INPUT_PULLUP);
  pinMode(opened,  INPUT_PULLUP); 
  pinMode(safe, INPUT_PULLUP);
   
  //Relay state
  digitalWrite(open,LOW);
  digitalWrite(close,LOW);
  digitalWrite(stop,LOW);
  digitalWrite(sensor,LOW);
 
  Serial.write("RRCI#"); //init string
   
}

void loop() {
  Timer();

  if (digitalRead(safe) == LOW){
    
     digitalWrite(led, HIGH); // Turn the LED on
  }
  else if (digitalRead(safe)  == HIGH){
    
    digitalWrite(led, LOW); // Turn the LED off
  }
  
  //Verify connection by serial
  while (Serial.available()>0) {
    //Read  Serial data and alocate on serialin
 
    serialin = Serial.readStringUntil('#');

     
     if (serialin == "on"){ // turn scope sensor on
      digitalWrite(sensor,HIGH);
     
      }

     if (serialin == "off"){ // turn scope sensor off
      digitalWrite(sensor,LOW);
     
      } 
  
    if (serialin ==  "x"){ 
      digitalWrite(open,LOW);
     
      }
    
    else  if (serialin == "open"){ 
        if (digitalRead(sensor) == LOW){//turn on  IR scope sensor
           digitalWrite(sensor,HIGH);
        }
        delay(1000);
        if (digitalRead(safe) == LOW){//open only if scope safe
           digitalWrite(open,HIGH);
           //delay(1000);
          digitalWrite(sensor,LOW);
        }
      }
      if (serialin == "y"){ 
      digitalWrite(close,LOW);
      
      }
   
    else if (serialin == "close"){ 
        if  (digitalRead(sensor) == LOW){//turn on IR scope sensor
           digitalWrite(sensor,HIGH);
        }
        delay(1000);
        
        
        if (digitalRead(safe)  == LOW){//close only if scope safe
           digitalWrite(close,HIGH);
           //delay(1000);
           digitalWrite(sensor,LOW);
        }
       
      }
  }  

  if (digitalRead(closed) == LOW) { //stop relays when 'closed' reached
      if  (digitalRead(close) == HIGH){//relays low if it was high
      digitalWrite(close,LOW);
      }
     
  }
if (digitalRead(opened) == LOW) {  //stop relays when  'opened' reached
       
      if (digitalRead(open) == HIGH){//relays low  if it was high
      digitalWrite(open,LOW);
      }
  }
if (serialin  == "Parkstatus"){ // exteranl query command to fetch RRCI data
  
  Serial.println("0#");
   serialin = ""; 
  }
 
if (serialin == "get"){ // exteranl query  command to fetch RRCI data - Two Pipelines(||) to make a boolean OR Comparission
  
  if (digitalRead(opened) == LOW){
     str += "opened,"; 
        
  }
  else if (digitalRead(closed) == LOW){
     str += "closed,";
  }
  
  if ((digitalRead(closed) == HIGH) && (digitalRead(opened) == HIGH)){
       str += "unknown,";
  }
  
  if (digitalRead(safe) == LOW){
     str += "safe,";
     
  }
  else if (digitalRead(safe) == HIGH){
    str += "unsafe,";
    
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

}
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