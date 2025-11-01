import requests
import time
from datetime import datetime

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def test_weather_device():
  print("Weather Device Test with NINA Logging")
print("=" * 40)
    
    # Check ArduSafeMon device
  print(f"[{get_timestamp()}] Testing ArduSafeMon at 192.168.1.99...")
    try:
   response = requests.get("http://192.168.1.99", timeout=5)
   if response.status_code == 200:
            print(f"[{get_timestamp()}] ? ArduSafeMon is responding")
            if "SAFE" in response.text:
    print(f"[{get_timestamp()}]    Status: SAFE")
            elif "NOT SAFE" in response.text:
   print(f"[{get_timestamp()}]    Status: NOT SAFE")
        else:
     print(f"[{get_timestamp()}] ? Device returned {response.status_code}")
    except Exception as e:
      print(f"[{get_timestamp()}] ? Device not reachable: {e}")
    
    print()
    
    # Check NINA Safety Monitor
    print(f"[{get_timestamp()}] Testing NINA Safety Monitor API...")
    try:
      response = requests.get("http://localhost:1888/v2/api/equipment/safetymonitor/info", timeout=5)
        if response.status_code == 200:
    data = response.json().get("Response", {})
            connected = data.get("Connected", False)
            name = data.get("Name", "Unknown")
            print(f"[{get_timestamp()}] ? NINA Safety Monitor API responding")
            print(f"[{get_timestamp()}]    Connected: {connected}")
       print(f"[{get_timestamp()}]    Device: {name}")
      if connected:
    is_safe = data.get("IsSafe", None)
    print(f"[{get_timestamp()}]    Is Safe: {is_safe}")
    else:
      print(f"[{get_timestamp()}] ? NINA API returned {response.status_code}")
    except Exception as e:
        print(f"[{get_timestamp()}] ? NINA API not reachable: {e}")
 
    print()
    print(f"[{get_timestamp()}] Monitoring for 10 seconds...")
    print("   (Watch NINA TRACE logs for API activity)")
  
    # Monitor for 10 seconds with API calls
    for i in range(10):
     print(f"[{get_timestamp()}] Monitoring... {10-i}s remaining")
  
        # Make API calls to generate NINA log activity
      try:
            requests.get("http://localhost:1888/v2/api/equipment/safetymonitor/info", timeout=3)
      except:
       pass
        
time.sleep(1)
    
    print()
    print(f"[{get_timestamp()}] ? Test completed!")
    print("Check NINA TRACE logs for entries like:")
    print("TRACE|API.cs|OnRequestAsync|157|Request: http://localhost:1888/v2/api/equipment/safetymonitor/info")

if __name__ == "__main__":
    test_weather_device()