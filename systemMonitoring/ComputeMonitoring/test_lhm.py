import requests
import json
from xml.etree import ElementTree as ET

# LibreHardwareMonitor remote server settings
LHM_SERVER_URL = "http://localhost:8085/data.json"

def test_lhm_connection():
    """Test connection to LibreHardwareMonitor and display available sensors"""
    print("Testing LibreHardwareMonitor connection...")
    print(f"URL: {LHM_SERVER_URL}")
    print("-" * 60)
    
    try:
        response = requests.get(LHM_SERVER_URL, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Successfully connected to LibreHardwareMonitor!")
            print("\nAvailable hardware and sensors:")
            print("-" * 60)
            
            display_hardware_tree(data, 0)
            
            print("\n" + "=" * 60)
            print("CPU TEMPERATURE READINGS:")
            print("=" * 60)
            
            cpu_temps = find_cpu_temperatures(data)
            if cpu_temps:
                for temp_info in cpu_temps:
                    print(f"📊 {temp_info['name']}: {temp_info['value']}")
            else:
                print("❌ No CPU temperature sensors found")
                
        else:
            print(f"❌ Failed to connect. Status code: {response.status_code}")
            
    except requests.ConnectionError:
        print("❌ Connection failed. Is LibreHardwareMonitor running with remote server enabled?")
        print("\nTo enable LibreHardwareMonitor remote server:")
        print("1. Open LibreHardwareMonitor")
        print("2. Go to Options > Remote Web Server")
        print("3. Check 'Run Web Server'")
        print("4. Set Port to 8085 (default)")
        print("5. Click OK")
        
    except requests.Timeout:
        print("❌ Connection timeout. LibreHardwareMonitor may be slow to respond.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def display_hardware_tree(node, indent=0):
    """Recursively display the hardware tree structure"""
    prefix = "  " * indent
    node_text = node.get("Text", "Unknown")
    node_value = node.get("Value", "")
    
    if node_value:
        print(f"{prefix}🔹 {node_text}: {node_value}")
    else:
        print(f"{prefix}📁 {node_text}")
    
    for child in node.get("Children", []):
        display_hardware_tree(child, indent + 1)

def find_cpu_temperatures(data):
    """Find all CPU temperature readings"""
    cpu_temps = []
    
    def search_node(node, hardware_name=""):
        node_text = node.get("Text", "")
        node_value = node.get("Value", "")
        
        # Check if this is a CPU hardware node
        if node_text.lower().startswith("cpu") and not hardware_name:
            hardware_name = node_text
        
        # Check if this is a temperature sensor
        if (node_value and "°C" in node_value and 
            hardware_name and "cpu" in hardware_name.lower()):
            cpu_temps.append({
                "hardware": hardware_name,
                "name": f"{hardware_name} - {node_text}",
                "value": node_value
            })
        
        # Recursively search children
        for child in node.get("Children", []):
            search_node(child, hardware_name)
    
    for hardware in data.get("Children", []):
        search_node(hardware)
    
    return cpu_temps

def get_simple_cpu_temp():
    """Get a simple CPU temperature reading"""
    try:
        response = requests.get(LHM_SERVER_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # Look for CPU package temperature
            for hardware in data.get("Children", []):
                if hardware.get("Text", "").lower().startswith("cpu"):
                    for sensor_group in hardware.get("Children", []):
                        if "temperature" in sensor_group.get("Text", "").lower():
                            for sensor in sensor_group.get("Children", []):
                                sensor_text = sensor.get("Text", "")
                                if any(keyword in sensor_text.lower() for keyword in ["package", "average"]):
                                    temp_value = sensor.get("Value", "")
                                    if temp_value and "°C" in temp_value:
                                        try:
                                            temp = float(temp_value.replace("°C", "").strip())
                                            return round(temp, 1)
                                        except ValueError:
                                            continue
            
            print("Could not find CPU package temperature, showing first CPU temp found:")
            # Fallback: get the first CPU temperature found
            for hardware in data.get("Children", []):
                if hardware.get("Text", "").lower().startswith("cpu"):
                    for sensor_group in hardware.get("Children", []):
                        if "temperature" in sensor_group.get("Text", "").lower():
                            for sensor in sensor_group.get("Children", []):
                                temp_value = sensor.get("Value", "")
                                if temp_value and "°C" in temp_value:
                                    try:
                                        temp = float(temp_value.replace("°C", "").strip())
                                        return round(temp, 1)
                                    except ValueError:
                                        continue
                                        
    except Exception as e:
        print(f"Error getting CPU temperature: {e}")
    
    return None

if __name__ == "__main__":
    test_lhm_connection()
    
    print("\n" + "=" * 60)
    print("SIMPLE CPU TEMPERATURE TEST:")
    print("=" * 60)
    
    temp = get_simple_cpu_temp()
    if temp:
        print(f"🌡️  Current CPU Temperature: {temp}°C")
    else:
        print("❌ Unable to get CPU temperature")
    
    print("\n" + "=" * 60)
    print("INTEGRATION READY!")
    print("=" * 60)
    print("If the temperature reading above is successful, you can now run:")
    print("python minipc_sys_lhm.py")
