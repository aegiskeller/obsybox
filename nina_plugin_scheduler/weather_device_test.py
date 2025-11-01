#!/usr/bin/env python3
"""
Test weather device connection/disconnection with NINA logging
Simulates connecting and disconnecting the ArduSafeMon weather device
"""
import requests
import time
from datetime import datetime
import json

# ArduSafeMon device configuration
ARDUSAFEMON_IP = "192.168.1.99"
ARDUSAFEMON_URL = f"http://{ARDUSAFEMON_IP}"

# NINA API configuration  
NINA_API_URL = "http://localhost:1888/v2/api"

def get_timestamp():
    """Get current timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_ardusafemon_status():
    """Check if ArduSafeMon weather device is responding"""
    try:
        print(f"[{get_timestamp()}] Checking ArduSafeMon at {ARDUSAFEMON_URL}...")
        response = requests.get(ARDUSAFEMON_URL, timeout=5)
        if response.status_code == 200:
        print(f"[{get_timestamp()}] ? ArduSafeMon is responding")
            
  # Try to extract weather status from the HTML response
     html = response.text
  if "SAFE" in html:
   print(f"[{get_timestamp()}]    Status: SAFE")
elif "NOT SAFE" in html:
         print(f"[{get_timestamp()}]    Status: NOT SAFE")
     
   return True
        else:
            print(f"[{get_timestamp()}] ? ArduSafeMon returned status {response.status_code}")
   return False
    except requests.exceptions.RequestException as e:
      print(f"[{get_timestamp()}] ? ArduSafeMon not reachable: {e}")
        return False

def check_nina_safety_monitor():
    """Check if NINA has a safety monitor connected"""
    try:
 response = requests.get(f"{NINA_API_URL}/equipment/safetymonitor/info", timeout=5)
   if response.status_code == 200:
  data = response.json().get("Response", {})
   connected = data.get("Connected", False)
            is_safe = data.get("IsSafe", None)
            name = data.get("Name", "Unknown")
      
            print(f"[{get_timestamp()}] NINA Safety Monitor:")
    print(f"[{get_timestamp()}]  Connected: {connected}")
 print(f"[{get_timestamp()}]    Device: {name}")
   if connected:
           print(f"[{get_timestamp()}]    Is Safe: {is_safe}")
       return connected, is_safe
        else:
       print(f"[{get_timestamp()}] ? NINA Safety Monitor API error: {response.status_code}")
         return False, None
    except requests.exceptions.RequestException as e:
        print(f"[{get_timestamp()}] ? Cannot check NINA Safety Monitor: {e}")
        return False, None

def run_weather_device_test():
    """Run the weather device connect/disconnect test"""
    
    print("???  Weather Device Test with NINA Logging")
    print("=" * 50)
    print(f"Testing ArduSafeMon device at {ARDUSAFEMON_IP}")
    print("This test will check device status, wait 10s, then test disconnection")
    print()
    
  # Phase 1: Check initial status
    print("?? Phase 1: Checking initial device status...")
    device_online = check_ardusafemon_status()
    nina_connected, nina_safe = check_nina_safety_monitor()
    
  if device_online:
        print(f"[{get_timestamp()}] ? ArduSafeMon weather device is online")
    else:
      print(f"[{get_timestamp()}] ? ArduSafeMon weather device is offline")
    
 print()
    
    # Phase 2: Monitor for 10 seconds while device is active
    print("??  Phase 2: Monitoring for 10 seconds...")
    print("   (Watch NINA TRACE logs for API requests)")
    
    for i in range(10):
        print(f"[{get_timestamp()}] Monitoring... {10-i} seconds remaining")
   
        # Query both device and NINA during monitoring
        device_status = check_ardusafemon_status()
        nina_connected, nina_safe = check_nina_safety_monitor()
        
        time.sleep(1)
    
    print()
    
    # Phase 3: Simulate device issues
    print("?? Phase 3: Testing device disconnection simulation...")
    
  # We can't actually disconnect the device, but we can test what happens
    # when we can't reach it or if it reports unsafe conditions
    print(f"[{get_timestamp()}] Simulating device disconnection...")
    
    # Try to reach the device multiple times quickly to generate activity
    for attempt in range(3):
        print(f"[{get_timestamp()}] Connection attempt {attempt + 1}...")
device_responsive = check_ardusafemon_status()
        nina_connected, nina_safe = check_nina_safety_monitor()
        time.sleep(2)
    
    print()
    
    # Phase 4: Final status check
    print("?? Phase 4: Final status summary...")
    final_device_status = check_ardusafemon_status()
    final_nina_connected, final_nina_safe = check_nina_safety_monitor()
    
    print()
  print("?? Test Summary:")
 print(f" ArduSafeMon Device: {'? Online' if final_device_status else '? Offline'}")
    print(f"   NINA Safety Monitor: {'? Connected' if final_nina_connected else '? Disconnected'}")
    if final_nina_connected:
        print(f"   Safety Status: {'? Safe' if final_nina_safe else '? Unsafe'}")

    print()
    print("?? Expected NINA Log Entries:")
    print("   Look for TRACE entries like:")
    print("   2025-10-30T14:XX:XX.XXXX|TRACE|API.cs|OnRequestAsync|157|Request: http://localhost:1888/v2/api/equipment/safetymonitor/info")
    print()
    print("? Weather device test completed!")

if __name__ == "__main__":
  run_weather_device_test()