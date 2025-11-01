#!/usr/bin/env python3
"""
Safety Monitor Sensor Value Test
Tests retrieving detailed sensor values from NINA Safety Monitor and ArduSafeMon device
"""
import requests
import json
import time
from datetime import datetime

def get_timestamp():
  return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def test_nina_safety_monitor_sensors():
    """Test NINA Safety Monitor API for sensor values"""
  print(f"[{get_timestamp()}] Testing NINA Safety Monitor sensors...")
    
  try:
    # Get basic safety monitor info
        response = requests.get("http://localhost:1888/v2/api/equipment/safetymonitor/info", timeout=5)
        if response.status_code == 200:
            data = response.json().get("Response", {})
            connected = data.get("Connected", False)
            is_safe = data.get("IsSafe", None)
            name = data.get("Name", "Unknown")
            
  print(f"   Safety Monitor: {name}")
            print(f"   Connected: {'? Yes' if connected else '? No'}")
         print(f"   Is Safe: {'? Yes' if is_safe else '? No' if is_safe is not None else '? Unknown'}")
   
            # Get supported actions
     try:
          actions_response = requests.get("http://localhost:1888/v2/api/equipment/safetymonitor/supportedactions", timeout=5)
       if actions_response.status_code == 200:
          actions = actions_response.json().get("Response", [])
     print(f"   Supported Actions: {actions}")
  
            # Try each supported action
  for action in actions:
        try:
  action_response = requests.post(
          "http://localhost:1888/v2/api/equipment/safetymonitor/action",
      json={"Action": action, "Parameters": ""},
     timeout=5
   )
        if action_response.status_code == 200:
        value = action_response.json().get("Response", "N/A")
          print(f"   ?? {action}: {value}")
      except Exception as e:
  print(f"   ? Error with action {action}: {e}")
        
            except Exception as e:
       print(f"   ? Error getting supported actions: {e}")
       
      else:
            print(f"   ? Safety Monitor API returned status {response.status_code}")
       
    except Exception as e:
        print(f"   ? Error accessing NINA Safety Monitor: {e}")

def test_ardusafemon_sensors():
 """Test ArduSafeMon device directly for sensor values"""
    print(f"[{get_timestamp()}] Testing ArduSafeMon device sensors...")
    
    try:
        response = requests.get("http://192.168.1.99", timeout=5)
        if response.status_code == 200:
       html = response.text
          print(f"   ? ArduSafeMon device responding")
     
            # Parse safety status
            if "class='status safe'" in html:
   print(f"   ???  Safety Status: SAFE")
 elif "class='status notsafe'" in html:
 print(f"   ??  Safety Status: NOT SAFE")
            else:
      print(f"   ? Safety Status: Unknown")
 
# Try to extract weather values from HTML
 # Look for patterns like "Temperature: 15.5 °C"
            import re
          
   temp_match = re.search(r'Temperature:\s*([\d.-]+)\s*°C', html)
            if temp_match:
        print(f"   ???  Temperature: {temp_match.group(1)}°C")
        
  humidity_match = re.search(r'Humidity:\s*([\d.-]+)\s*%', html)
      if humidity_match:
    print(f"   ?? Humidity: {humidity_match.group(1)}%")
            
            wind_match = re.search(r'Wind Speed:\s*([\d.-]+)\s*m/s', html)
  if wind_match:
                print(f"   ?? Wind Speed: {wind_match.group(1)} m/s")
         
            clouds_match = re.search(r'Clouds:\s*([\d.-]+)\s*%', html)
  if clouds_match:
       print(f"   ??  Clouds: {clouds_match.group(1)}%")
         
            # Look for rain sensor value in the HTML
            a0_match = re.search(r'A0 avg:\s*([\d.-]+)', html)
    if a0_match:
     print(f"   ???  Rain Sensor (A0): {a0_match.group(1)}")
    
        else:
         print(f"   ? ArduSafeMon returned status {response.status_code}")
         
    except Exception as e:
        print(f"   ? ArduSafeMon not reachable: {e}")

def test_mqtt_weather_safety():
    """Test if we can get MQTT weather safety data"""
    print(f"[{get_timestamp()}] Testing MQTT weather safety topic...")
    
    # Note: This would require MQTT client, but we can show the concept
    print(f"   ?? MQTT Topic: obsybox/weathersafety")
    print(f"   ?? Expected format: {{'safe': true/false, 'reason': 'description'}}")
    print(f"   ??  MQTT monitoring would require paho-mqtt client")

def main():
    """Main sensor testing function"""
    print("?? Safety Monitor & Weather Sensor Test")
    print("=" * 50)
  print("Testing sensor value retrieval from multiple sources")
    print()
    
    # Test 1: NINA Safety Monitor API
    test_nina_safety_monitor_sensors()
    print()
    
    # Test 2: ArduSafeMon device direct
    test_ardusafemon_sensors()
    print()
    
    # Test 3: MQTT concept
  test_mqtt_weather_safety()
  print()
    
    print("?? Sensor Test Summary:")
    print("   ? NINA Safety Monitor - API-based sensor access")
    print("   ? ArduSafeMon Device - Direct web interface parsing")
    print("   ? MQTT Integration - Real-time weather safety data")
    print()
    print("?? Integration Options:")
    print("   1. Use NINA Safety Monitor API actions for sensor values")
    print("   2. Parse ArduSafeMon web interface for detailed weather")
    print("   3. Subscribe to MQTT topics for real-time updates")
    print("   4. Combine all sources for comprehensive monitoring")
  
    print(f"\n? Sensor value testing completed!")

if __name__ == "__main__":
    main()