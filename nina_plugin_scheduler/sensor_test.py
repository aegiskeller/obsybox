import requests
import re

def get_ardusafemon_sensors():
    """Get sensor values directly from ArduSafeMon device"""
    print("ArduSafeMon Sensor Values:")
    print("-" * 30)
    
    try:
        response = requests.get("http://192.168.1.99", timeout=5)
        if response.status_code == 200:
            html = response.text
            print("? Device responding")
            
            # Extract rain sensor value (A0)
            a0_match = re.search(r'A0 avg:\s*([\d.-]+)', html)
            if a0_match:
                print(f"???  Rain Sensor (A0): {a0_match.group(1)}")
            
            # Extract temperature
            temp_match = re.search(r'Temperature:\s*([\d.-]+)', html)
            if temp_match:
                print(f"???  Temperature: {temp_match.group(1)}°C")
       
            # Extract humidity
            humidity_match = re.search(r'Humidity:\s*([\d.-]+)', html)
            if humidity_match:
                print(f"?? Humidity: {humidity_match.group(1)}%")
          
            # Extract wind speed
            wind_match = re.search(r'Wind Speed:\s*([\d.-]+)', html)
            if wind_match:
                print(f"?? Wind: {wind_match.group(1)} m/s")
       
            # Extract clouds
            clouds_match = re.search(r'Clouds:\s*([\d.-]+)', html)
            if clouds_match:
                print(f"??  Clouds: {clouds_match.group(1)}%")
            
            # Safety status
            if 'status safe' in html:
                print("???  Status: SAFE")
            elif 'status notsafe' in html:
                print("??  Status: NOT SAFE")
        
        else:
            print(f"? Device returned status {response.status_code}")
 
    except Exception as e:
        print(f"? Error: {e}")

def get_nina_safety_status():
    """Get basic safety status from NINA"""
    print("\nNINA Safety Monitor:")
    print("-" * 20)
    
    try:
        response = requests.get("http://localhost:1888/v2/api/equipment/safetymonitor/info", timeout=5)
        if response.status_code == 200:
            data = response.json().get("Response", {})
            connected = data.get("Connected", False)
            is_safe = data.get("IsSafe", None)
            
            print(f"Connected: {'? Yes' if connected else '? No'}")
            print(f"Is Safe: {'? Yes' if is_safe else '? No' if is_safe is not None else '? Unknown'}")
       
        else:
            print(f"? API returned status {response.status_code}")
   
    except Exception as e:
        print(f"? Error: {e}")

if __name__ == "__main__":
    print("?? Safety Monitor Sensor Test")
    print("=" * 40)
    
    # Get values from ArduSafeMon device
    get_ardusafemon_sensors()
    
    # Get values from NINA
    get_nina_safety_status()
 
    print("\n? Sensor test completed!")
    print("\n?? Summary:")
    print("? ArduSafeMon provides: rain sensor, weather data, safety status")
    print("? NINA provides: safety monitor connection status")
    print("? Can integrate both sources for comprehensive monitoring")