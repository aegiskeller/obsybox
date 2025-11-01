import requests
import time
import json

def monitor_nina_status():
    """Monitor NINA application status and show what you should see"""
    print("?? NINA Application Monitoring Guide")
    print("=" * 50)
    
    try:
        # Check NINA API status
        response = requests.get("http://localhost:1888/v2/api/version", timeout=5)
        if response.status_code == 200:
            version = response.json().get("Response", "Unknown")
            print(f"? NINA API Active - Version: {version}")
            print("\n?? What you should see in NINA:")
            print("   1. Equipment Tab - Device connection status")
            print("   2. Status Bar - API request indicators")
            print("   3. Log Window - API activity messages")
        else:
            print("? NINA API not responding")
            return
    except Exception as e:
        print(f"? Cannot connect to NINA: {e}")
        return
    
    print("\n?? Current Equipment Status in NINA:")
    print("   (This should match what you see in NINA's Equipment tab)")
    
    equipment = {
        "Camera": "/v2/api/equipment/camera/info",
        "Mount": "/v2/api/equipment/mount/info", 
        "Dome": "/v2/api/equipment/dome/info",
        "Focuser": "/v2/api/equipment/focuser/info",
      "FilterWheel": "/v2/api/equipment/filterwheel/info"
  }
    
    for name, endpoint in equipment.items():
try:
            response = requests.get(f"http://localhost:1888{endpoint}", timeout=5)
  if response.status_code == 200:
  data = response.json().get("Response", {})
    connected = data.get("Connected", False)
    device_name = data.get("Name", "No device")
      status = "?? Connected" if connected else "?? Disconnected"
     print(f"   {name:12}: {status} ({device_name})")
       else:
print(f"   {name:12}: ? API Error")
     except Exception:
            print(f"   {name:12}: ? Request Failed")
    
    print("\n?? To Enable NINA Monitoring:")
    print("1. Open NINA application")
    print("   2. Go to Options ? General ? Logging")
    print("   3. Set log level to 'Debug' or 'Info'")
 print("   4. Enable 'Show log window'")
    print(" 5. Watch for API entries when running tests")
    
    print("\n?? Expected NINA Interface Updates:")
    print(" • Equipment icons change color based on connection")
    print("   • Status messages appear in bottom status bar")
    print("   • Log entries show API requests and responses")
    print("   • Equipment properties update in real-time")

def test_with_nina_feedback():
 """Run a test that should show visible changes in NINA"""
    print("\n?? Running Live Test with NINA Feedback")
    print("   Watch NINA application while this runs...")
    
    for i in range(3):
        print(f"\n?? Test {i+1}/3: Querying NINA equipment...")
        
        # Query each piece of equipment
        equipment = ["camera", "mount", "dome", "focuser"]
        for device in equipment:
            try:
response = requests.get(f"http://localhost:1888/v2/api/equipment/{device}/info", timeout=3)
    if response.status_code == 200:
        print(f"   ? {device.capitalize()} queried successfully")
                else:
      print(f"   ? {device.capitalize()} query returned {response.status_code}")
            except Exception as e:
   print(f"   ? {device.capitalize()} query failed: {e}")
  
        print(f"   ?? Waiting 3 seconds... (check NINA log window)")
        time.sleep(3)
    
print("\n? Test complete! Check NINA for:")
    print("   • Log entries showing API requests")
    print("   • Equipment status updates") 
    print("   • Any status bar messages")

if __name__ == "__main__":
    monitor_nina_status()
    
    # Ask user if they want to run live test
    print("\n" + "="*50)
    response = input("?? Run live test to see NINA updates? (y/N): ")
    if response.lower() in ['y', 'yes']:
        test_with_nina_feedback()
    else:
        print("? Monitoring complete. Check NINA interface as described above.")