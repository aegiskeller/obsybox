import requests
import time
import json

print("obsybox NINA API Test - Verbose Mode")
print("=" * 45)
print("?? Check NINA Log Window for API activity...")
print()

def test_api_with_logging():
    """Test API with detailed logging to help see NINA activity"""
    
    # Test 1: Version check
    print("?? Test 1: Getting NINA version...")
  try:
    response = requests.get("http://localhost:1888/v2/api/version", timeout=5)
        print(f"   Request: GET /v2/api/version")
    print(f"   Response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
            print(f"   Version: {data.get('Response', 'Unknown')}")
       print(f"   ? NINA should log this API request")
        time.sleep(2)
    except Exception as e:
    print(f"   ? Error: {e}")
    
    print()
    
    # Test 2: Equipment queries (should show in NINA Equipment tab)
    equipment_endpoints = [
        ("Camera", "/v2/api/equipment/camera/info"),
        ("Mount", "/v2/api/equipment/mount/info"),
        ("Dome", "/v2/api/equipment/dome/info"),
     ("Focuser", "/v2/api/equipment/focuser/info")
    ]
    
    print("?? Test 2: Querying equipment status...")
    for name, endpoint in equipment_endpoints:
     print(f"   Querying {name}...")
        try:
  response = requests.get(f"http://localhost:1888{endpoint}", timeout=5)
     print(f"   Request: GET {endpoint}")
      print(f"   Response: {response.status_code}")
            
          if response.status_code == 200:
    data = response.json().get("Response", {})
       connected = data.get("Connected", False)
      device_name = data.get("Name", "Unknown")
       print(f"   Status: {'?? Connected' if connected else '?? Disconnected'}")
    print(f"   Device: {device_name}")
     print(f"   ? Check NINA Equipment tab - {name} status should update")
          else:
         print(f" ? Unexpected response code")
     
       time.sleep(1)  # Give time to see updates in NINA
        except Exception as e:
       print(f"   ? Error: {e}")
        print()
    
    # Test 3: Multiple rapid requests (should show activity)
    print("?? Test 3: Rapid API requests (watch NINA logs)...")
    for i in range(5):
        print(f"   Request {i+1}/5: Checking NINA version...")
        try:
response = requests.get("http://localhost:1888/v2/api/version", timeout=3)
            if response.status_code == 200:
    print(f"   ? Response {i+1} successful")
time.sleep(0.5)  # Half second between requests
        except Exception as e:
        print(f"   ? Request {i+1} failed: {e}")
    
    print()
    print("?? What to check in NINA:")
    print("   1. Log Window - Should show API GET requests")
    print("   2. Equipment Tab - Status indicators should reflect our queries")
    print("   3. Status Bar - May show API activity indicators")
print("   4. Network activity - NINA is receiving HTTP requests on port 1888")

if __name__ == "__main__":
    test_api_with_logging()
    
    print()
    print("=" * 45)
    print("? Verbose test complete!")
    print("?? Expected NINA log entries:")
    print("   [INFO] HTTP GET /v2/api/version")
    print("   [INFO] HTTP GET /v2/api/equipment/camera/info")
    print("   [INFO] HTTP GET /v2/api/equipment/mount/info")
    print("   [DEBUG] API request processed")
    print()
    print("?? If you see these logs, NINA API integration is working perfectly!")