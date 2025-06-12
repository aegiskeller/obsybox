// This is the master on the WeMos D1 R2 Mini
// following frying the SFT

#include <Wire.h>
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <Hash.h>
#include <ESPAsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include "arduino_secrets.h"

// Replace with your network credentials
char ssid[] = SECRET_SSID;        // your network SSID (name)
char pass[] = SECRET_PASS;    // your network password (use for WPA, or use as key for WEP)
IPAddress staticIP(192, 168, 1, 73);  // Replace with your desired static IP address
IPAddress gateway(192, 168, 1, 1);     // Replace with your gateway IP address
IPAddress subnet(255, 255, 255, 0);    // Replace with your subnet mask

// current temperature & humidity, updated in loop()
float at = 0.0;
float ah = 0.0;
float tt = 0.0;
float dp = 0.0;
float hh = 0.0;
const char* hm = "A"; // heater operational mode
float dt = 5.0; // inital delta T

char strsdt[10];
char dataPacket[12];

// LED
const int led_output = 5; 

String sliderValue = "5";
float sdt = 5.0;
const char* PARAM_INPUT = "value";
const char* PARAM_INPUT_1 = "state";


// Create AsyncWebServer object on port 80
AsyncWebServer server(80);


char datastr[35]={};    // empty array to put the data from the slave
volatile char cmd;      // char variable used by the master to command the slave

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dew Heater Control</title>
  <style>
    body {
      background: #181a20;
      color: #f1f1f1;
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      padding: 0;
      min-height: 100vh;
    }
    .container {
      max-width: 900px;
      margin: 2rem auto;
      display: flex;
      flex-wrap: wrap;
      gap: 2rem;
      justify-content: center;
    }
    .panel {
      background: #23262f;
      border-radius: 1rem;
      box-shadow: 0 2px 8px #0003;
      padding: 2rem 1.5rem;
      min-width: 270px;
      flex: 1 1 300px;
      border: 1px solid #292c36;
      margin-bottom: 1rem;
    }
    h2 {
      text-align: center;
      margin-top: 2rem;
      font-size: 2.2rem;
      font-weight: 400;
    }
    h3 {
      color: #1abc9c;
      font-size: 1.2rem;
      font-weight: 400;
      margin-bottom: 1em;
    }
    .dht-labels, .units, .note {
      color: #b0b3b8;
      font-size: 1rem;
    }
    .value {
      font-size: 2.2rem;
      font-weight: 600;
      margin-left: 0.5em;
    }
    .slider {
      width: 100%;
      margin: 1.5em 0;
      height: 6px;
      background: #333;
      border-radius: 3px;
      outline: none;
    }
    .slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #1abc9c;
      cursor: pointer;
      border: 2px solid #23262f;
      box-shadow: 0 2px 6px #0004;
    }
    .slider:focus { outline: none; }
    .switch {
      position: relative;
      display: inline-block;
      width: 48px;
      height: 24px;
      margin-left: 1em;
      vertical-align: middle;
    }
    .switch input { display: none; }
    .slider-switch {
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background: #444;
      border-radius: 24px;
      transition: background 0.2s;
    }
    .switch input:checked + .slider-switch {
      background: #1abc9c;
    }
    .slider-switch:before {
      position: absolute;
      content: "";
      height: 20px; width: 20px;
      left: 2px; bottom: 2px;
      background: #fff;
      border-radius: 50%;
      transition: transform 0.2s;
    }
    .switch input:checked + .slider-switch:before {
      transform: translateX(24px);
    }
    .note {
      font-size: 0.95em;
      margin-top: 0.5em;
    }
    @media (max-width: 800px) {
      .container { flex-direction: column; gap: 1rem; }
      .panel { min-width: unset; }
    }
  </style>
</head>
<body>
  <h2>Telescope Dew Heater</h2>
  <div class="container">
    <div class="panel">
      <h3>Ambient</h3>
      <div>
        <span class="dht-labels">Temperature</span>
        <span class="value" id="ambtemp">%AMBTEMP%</span>
        <span class="units">&deg;C</span>
      </div>
      <div>
        <span class="dht-labels">Humidity</span>
        <span class="value" id="ambhum">%AMBHUM%</span>
        <span class="units">&percnt;</span>
      </div>
    </div>
    <div class="panel">
      <h3>Telescope</h3>
      <div>
        <span class="dht-labels">Temperature</span>
        <span class="value" id="teltemp">%TELTEMP%</span>
        <span class="units">&deg;C</span>
      </div>
      <div>
        <span class="dht-labels">Dew Point</span>
        <span class="value" id="dewpt">%DEWPT%</span>
        <span class="units">&deg;C</span>
      </div>
      <div>
        <span class="dht-labels">Heater Power</span>
        <span class="value" id="htrpwr">%HTRPWR%</span>
        <span class="units">&percnt;</span>
      </div>
    </div>
    <div class="panel">
      <h3>Operational</h3>
      <div>
        <span class="dht-labels">&Delta;T</span>
        <span class="value" id="deltat">%DELTAT%</span>
        <span class="units">&deg;C</span>
      </div>
      <div class="note" id="outputmodestate">%OUTPUTMODESTATE%</div>
      <div class="note">A = Ambient Offset &nbsp;|&nbsp; D = Dew Point Offset</div>
    </div>
    <div class="panel">
      <h3>User Options</h3>
      <div style="margin-bottom:1em;">
        <span id="textSliderValue">Set &Delta;T: %SLIDERVALUE% &deg;C</span>
        <input type="range" onchange="updateSliderDT(this)" value="5" id="DTSlider" min="0" max="9" step="0.1" class="slider">
      </div>
      <div id="buttonholder">%BUTTONPLACEHOLDER%</div>
    </div>
  </div>
  <script>
    setInterval(function () {
      fetch("/ambtemp").then(r=>r.text()).then(t=>document.getElementById("ambtemp").innerHTML=t);
      fetch("/ambhum").then(r=>r.text()).then(t=>document.getElementById("ambhum").innerHTML=t);
      fetch("/teltemp").then(r=>r.text()).then(t=>document.getElementById("teltemp").innerHTML=t);
      fetch("/dewpt").then(r=>r.text()).then(t=>document.getElementById("dewpt").innerHTML=t);
      fetch("/heaterpower").then(r=>r.text()).then(t=>document.getElementById("htrpwr").innerHTML=t);
      fetch("/deltat").then(r=>r.text()).then(t=>document.getElementById("deltat").innerHTML=t);
      fetch("/outputmodestate").then(r=>r.text()).then(t=>document.getElementById("outputmodestate").innerHTML=t);
    }, 10000);

    function updateSliderDT(element) {
      var sliderValue = document.getElementById("DTSlider").value;
      document.getElementById("textSliderValue").innerHTML = "Set &Delta;T: " + sliderValue + "&deg;C";
      fetch("/slider?value=" + sliderValue);
    }

    function toggleCheckbox(element) {
      if(element.checked){
        fetch("/update?state=1");
      } else {
        fetch("/update?state=0");
      }
    }

    function setHmMode(mode) {
      let state = (mode === "D") ? 1 : 0;
      fetch("/update?state=" + state);
    }

    // On page load, set the radio button based on current mode
    window.addEventListener('DOMContentLoaded', function() {
      fetch("/outputmodestate").then(r=>r.text()).then(mode=>{
        if(mode.trim() === "D") {
          document.getElementById("hmD").checked = true;
        } else {
          document.getElementById("hmA").checked = true;
        }
      });
    });
  </script>
  <script>
  setTimeout(function() {
    location.reload();
  }, 10000); // 10000 ms = 10 seconds
</script>
</body>
</html>
)rawliteral";

// Replaces placeholder with DHT values
String processor(const String& var){
  //Serial.println(var);
  if(var == "AMBTEMP"){
    return String(at);
  }
  else if(var == "AMBHUM"){
    return String(ah);
  }
  else if(var == "TELTEMP"){
    return String(tt);
  }
  else if(var == "DEWPT"){
    return String(dp);
  }
  else if(var == "HTRPWR"){
    return String(hh);
  }
  else if(var == "OUTPUTMODESTATE"){
    if (hm == "A"){
      return String("Ambient Offset");
    }
    else if (hm == "D"){
      return String("Dewpoint Offset");
    }
    else {
      return String("Undefined");      
    }
  }
  else if(var == "DELTAT"){
    return String(dt);
  }
  else if(var == "SLIDERVALUE"){
    return sliderValue;
  }
  else if(var == "BUTTONPLACEHOLDER"){
  String buttons = "";
  buttons += "<div style=\"margin-top:1em;\">";
  buttons += "<label><input type=\"radio\" name=\"hm_mode\" value=\"A\" id=\"hmA\" onclick=\"setHmMode('A')\"> Above Ambient</label>";
  buttons += "<label style=\"margin-left:2em;\"><input type=\"radio\" name=\"hm_mode\" value=\"D\" id=\"hmD\" onclick=\"setHmMode('D')\"> Above Dewpoint</label>";
  buttons += "</div>";
  return buttons;
}
  return String();
}


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

void ServerNotFound(AsyncWebServerRequest *request) {
  request->send(404, "text/plain", "Not found");
}

void setup() {
  Serial.begin(9600); /* begin serial for debug */
  Wire.begin(); /* join i2c bus with std settings */
  
  // Connect to Wi-Fi
  WiFi.config(staticIP, gateway, subnet);
  WiFi.begin(ssid, pass);
  Serial.println("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }

  // Print ESP8266 Local IP Address
  Serial.println(WiFi.localIP());
  
  // Route for root / web page
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/html", index_html, processor);
  });
  server.on("/ambtemp", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", String(at).c_str());
  });
  server.on("/ambhum", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", String(ah).c_str());
  });
  server.on("/teltemp", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", String(tt).c_str());
  });
  server.on("/dewpt", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", String(dp).c_str());
  });
  server.on("/heaterpower", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", String(hh).c_str());
  });
  server.on("/deltat", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", String(dt).c_str());
  });
  server.on("/outputmodestate", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send_P(200, "text/plain", hm);
  });
  server.on("/slider", HTTP_GET, [] (AsyncWebServerRequest *request){
    String inputMessage_slider;
    if (request->hasParam(PARAM_INPUT)){
      inputMessage_slider = request->getParam(PARAM_INPUT)->value();
      sliderValue = inputMessage_slider;
      sdt = sliderValue.toFloat();
    }
    else {
      inputMessage_slider = "No Message Sent";
    }
    Serial.println(inputMessage_slider);
    request->send(200, "text/plain", "OK");
  });

  // Send a GET request to /update?state=<inputMessage>
  server.on("/update", HTTP_GET, [] (AsyncWebServerRequest *request) {
    String inputMessage_button;
    // GET input1 value on /update?state=<inputMessage>
    if (request->hasParam(PARAM_INPUT_1)) {
      inputMessage_button = request->getParam(PARAM_INPUT_1)->value();
      if (inputMessage_button == "0"){
        hm = "A";
      }
      else if (inputMessage_button == "1"){
        hm = "D";
      }
   }
    else {
      inputMessage_button = "No message sent";
    }
    Serial.print("inputMessage_button: ");
    Serial.println(inputMessage_button);
    request->send(200, "text/plain", "OK");
  });

  server.onNotFound(ServerNotFound);

  // Start server
  server.begin();

}

void loop() {
  Wire.beginTransmission(0x08); /* begin with device address 8 */
  /* Construct the Master message */
  /* part one is the delta t requested */
  dtostrf(sdt,3,1,strsdt);
  /* part two is the operational mode */
  strcpy(dataPacket, strsdt);
  strcat(dataPacket, ";");
  strcat(dataPacket, hm);
  Wire.write(dataPacket);  /* sends a short cmd */
  Wire.endTransmission();    /* stop transmitting */
  Serial.print("Sent data to the slave: ");
  Serial.println(dataPacket);
  Wire.requestFrom(0x08, 28);         // request the payload from the slave
  //gathers data comming from slave
  int i=0; //counter for each byte as it arrives
  while (Wire.available()) { 
    datastr[i] = Wire.read(); // every character that arrives it put in order in the empty array datastr
    i=i+1;
    yield();
  }
//  Serial.println(datastr);
  // parse this string
  String ambtemp = getValue(datastr, ';', 0);
  String ambhum = getValue(datastr, ';', 1);
  String teletemp = getValue(datastr, ';', 2);
  String deltat = getValue(datastr, ';', 3);
  String heater = getValue(datastr, ';', 4);
  String dewpt = getValue(datastr, ';', 5);
  char * end;
  Serial.println(ambtemp);
  Serial.println(ambhum);
  Serial.println(teletemp);
  Serial.println(deltat);
  Serial.println(heater);
  Serial.println(dewpt);
  at = strtod(ambtemp.c_str(), &end);
  ah = strtod(ambhum.c_str(), &end);
  tt = strtod(teletemp.c_str(), &end);
  dp = strtod(dewpt.c_str(), &end);
  hh = strtod(heater.c_str(), &end);
  dt = strtod(deltat.c_str(), &end);
  delay(5000);
}


