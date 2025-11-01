import requests
import time

print("obsybox NINA API Test with Safety Monitor Sensor Data")
print("=" * 55)

# Test NINA API
try:
    response = requests.get("http://localhost:1888/v2/api/version", timeout=5)
    if response.status_code == 200:
        version = response.json().get("Response", "Unknown")
        print(f"? NINA API connected! Version: {version}")
    else:
        print(f"? API error: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"? Cannot connect: {e}")
    exit(1)

# Test equipment including Safety Monitor
print("\nTesting equipment:")
endpoints = [
    ("Camera", "/v2/api/equipment/camera/info"),
    ("Mount", "/v2/api/equipment/mount/info"),
    ("Dome", "/v2/api/equipment/dome/info"),
    ("Safety Monitor", "/v2/api/equipment/safetymonitor/info")
]

for name, endpoint in endpoints:
    try:
        response = requests.get(f"http://localhost:1888{endpoint}", timeout=5)
        if response.status_code == 200:
            data = response.json().get("Response", {})
            connected = data.get("Connected", False)
            device_name = data.get("Name", "Unknown")
            status = "? Connected" if connected else "? Disconnected"
            print(f"   {name}: {status} ({device_name})")
            
            # Special handling for Safety Monitor - show sensor data
            if name == "Safety Monitor":
                is_safe = data.get("IsSafe", None)
                print(f"      Is Safe: {'? Yes' if is_safe else '? No' if is_safe is not None else '? Unknown'}")
        
    except Exception as e:
        print(f"   {name}: ? Error ({e})")

# Test Safety Monitor Actions (for sensor values)
print("\nTesting Safety Monitor sensor values:")
try:
    # Check for supported actions
    response = requests.get("http://localhost:1888/v2/api/equipment/safetymonitor/supportedactions", timeout=5)
    if response.status_code == 200:
        actions_data = response.json().get("Response", [])
        print(f"   Supported Actions: {actions_data}")
        
        # Try to get rain sensor value via Action
        if "RainSensorValue" in str(actions_data):
            response = requests.post("http://localhost:1888/v2/api/equipment/safetymonitor/action", 
    json={"Action": "RainSensorValue", "Parameters": ""}, 
   timeout=5)
            if response.status_code == 200:
                rain_value = response.json().get("Response", "N/A")
                print(f"   ???  Rain Sensor Value: {rain_value}")
            
        # Try to get unsafe reason via Action
        if "UnsafeReason" in str(actions_data):
            response = requests.post("http://localhost:1888/v2/api/equipment/safetymonitor/action", 
json={"Action": "UnsafeReason", "Parameters": ""}, 
          timeout=5)
            if response.status_code == 200:
                unsafe_reason = response.json().get("Response", "N/A")
                print(f"   ??  Unsafe Reason: {unsafe_reason}")
          
except Exception as e:
    print(f"   ? Error getting sensor values: {e}")

# Test ArduSafeMon device directly
print("\nTesting ArduSafeMon device directly:")
try:
    response = requests.get("http://192.168.1.99", timeout=5)
    if response.status_code == 200:
        print(f"   ? ArduSafeMon device responding")
        html = response.text
        
        # Extract status from HTML
        if "SAFE" in html and "NOT SAFE" not in html:
            print(f"   ???  Device Status: SAFE")
        elif "NOT SAFE" in html:
            print(f"   ??  Device Status: NOT SAFE")
        else:
            print(f"   ? Device Status: Unknown")
        
        # Try to extract weather data from HTML
        if "Temperature:" in html:
            print(f"   ???  Weather data available in device interface")
        if "Humidity:" in html:
            print(f"   ?? Humidity data available in device interface")
        if "Wind Speed:" in html:
            print(f"   ?? Wind data available in device interface")
    
    else:
        print(f"   ? ArduSafeMon device returned status {response.status_code}")
except Exception as e:
    print(f"   ? ArduSafeMon device not reachable: {e}")

# Simulate target scheduling
print("\nSimulating target scheduling:")
targets = [
    {"name": "M42 Orion Nebula", "ra": "05:35:17", "dec": "-05:23:14"},
    {"name": "M31 Andromeda Galaxy", "ra": "00:42:44", "dec": "+41:16:09"},
    {"name": "M13 Hercules Cluster", "ra": "16:41:41", "dec": "+36:27:37"}
]

for i, target in enumerate(targets, 1):
    print(f"?? Target {i}: {target['name']}")
    print(f"   Coordinates: RA {target['ra']}, Dec {target['dec']}")
    print(f"   ?? Waiting 3 seconds...")
    time.sleep(3)
    print(f"   ? Target {i} complete")

print("\n?? NINA API test with sensor data completed successfully!")
print("? Ready for scheduler integration with safety monitoring")