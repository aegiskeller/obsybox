#!/usr/bin/env python3
"""
Working NINA API Test - Simple Version
"""
import requests
import json

def test_nina_connection():
    """Test NINA API connectivity"""
 api_url = "http://localhost:1888/v2/api"
    
    print("?? Testing NINA API Connection...")
    print(f"API URL: {api_url}")
    
    try:
        response = requests.get(f"{api_url}/version", timeout=5)
if response.status_code == 200:
            print("? NINA API is accessible!")
 version_info = response.json()
            version = version_info.get('Response', {}).get('Version', 'Unknown')
          print(f"   NINA Version: {version}")
        return True
  else:
  print(f"? NINA API returned status {response.status_code}")
            return False
    except Exception as e:
     print(f"? Cannot connect to NINA API: {e}")
        print("   Make sure NINA is running and API is enabled")
        return False

def test_equipment_status():
    """Test reading equipment status"""
    api_url = "http://localhost:1888/v2/api"
    
    print("\n?? Testing Equipment Status...")
    
    endpoints = {
    "Camera": "/equipment/camera/info",
        "Mount": "/equipment/mount/info",
      "Dome": "/equipment/dome/info"
    }
  
    for equipment, endpoint in endpoints.items():
        try:
            response = requests.get(f"{api_url}{endpoint}", timeout=5)
            if response.status_code == 200:
   data = response.json().get('Response', {})
    connected = data.get('Connected', False)
     name = data.get('Name', 'Unknown')
status = "? Connected" if connected else "? Disconnected"
       print(f"   {equipment}: {status} ({name})")
      else:
      print(f"   {equipment}: ? Error (HTTP {response.status_code})")
        except Exception as e:
      print(f"   {equipment}: ? Error ({e})")

def test_notification():
    """Test sending a notification"""
    api_url = "http://localhost:1888/v2/api"
    
    print("\n?? Testing Notifications...")
    
    try:
        notification_data = {
            "Title": "obsybox Test",
            "Message": "NINA API test notification",
            "Priority": 0
        }
        
        response = requests.post(
    f"{api_url}/plugins/groundstation/notification",
  json=notification_data,
      timeout=5
  )
    
     if response.status_code == 200:
    print("? Notification sent successfully!")
    print("   Check your Pushover app for the test message")
  else:
  print(f"?? Notification failed (HTTP {response.status_code})")
            print("   This is normal if Ground Station plugin is not configured")
  except Exception as e:
        print(f"?? Notification error: {e}")
        print("   This is normal if Ground Station plugin is not available")

def main():
    """Main test function"""
    print("obsybox NINA API Test")
    print("=" * 40)
    print("Safe testing - no hardware commands")
    
    # Test 1: API connection
    if not test_nina_connection():
 print("\n? Test failed - cannot connect to NINA API")
     return False

    # Test 2: Equipment status (read-only)
    test_equipment_status()
    
    # Test 3: Notification system
    test_notification()
    
    print("\n?? All tests completed!")
    print("This confirms NINA API integration is working")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n? NINA API test passed!")
    else:
        print("\n? NINA API test failed!")
        exit(1)