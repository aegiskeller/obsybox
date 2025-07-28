import requests
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt

# NINA API settings
NINA_API_URL = "http://192.168.1.8:1888"
NINA_API_ENDPOINT_CAMERA = "/v2/api/equipment/camera/info"
NINA_API_ENDPOINT_STATUS = "/v2/api/version"
NINA_API_ENDPOINT_FOCUSER = "/v2/api/equipment/focuser/info"  # Added focuser endpoint
NINA_API_ENDPOINT_MOUNT = "/v2/api/equipment/telescope/info"  # Added mount endpoint
NINA_API_ENDPOINT_DOME = "/v2/api/equipment/dome/info"
NINA_API_ENDPOINT_FILTERWHEEL = "/v2/api/equipment/filterwheel/info"
NINA_API_ENDPOINT_GUIDER = "/v2/api/equipment/guider/info"  # Added guider endpoint

# MQTT settings
MQTT_BROKER = "192.168.1.49"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "obsybox/equipment"
MQTT_CLIENT_ID = "nina-monitor"

def get_timestamp():
    """Return current timestamp in a readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def query_nina_api(endpoint):
    """Query NINA API at the specified endpoint."""
    try:
        response = requests.get(f"{NINA_API_URL}{endpoint}", timeout=5)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[{get_timestamp()}] Error connecting to NINA API: {e}")
        return None

def check_camera_status():
    """Check if the camera is connected and get its temperature."""
    print(f"[{get_timestamp()}] Querying NINA for camera status...")
    
    # First check if NINA is running and connected
    status_data = query_nina_api(NINA_API_ENDPOINT_STATUS)
    if not status_data:
        print(f"[{get_timestamp()}] NINA API not reachable.")
        return False, None, None, False, 0
    
    # Now get camera info
    camera_data = query_nina_api(NINA_API_ENDPOINT_CAMERA)
    if not camera_data:
        print(f"[{get_timestamp()}] Cannot retrieve camera data.")
        return False, None, None, False, 0
    
    camera_info = camera_data.get("Response", {})
    if not camera_info.get("Connected", False):
        print(f"[{get_timestamp()}] Camera is not connected.")
        return False, None, None, False, 0

    # Get temperature if available
    temperature = camera_info.get("Temperature", None)
    # Get TargetTemp if available
    target_temp = camera_info.get("TargetTemp", None)
    # Get CoolerOn status
    cooler_on = camera_info.get("CoolerOn", False)
    # Get CoolerPower
    cooler_power = camera_info.get("CoolerPower", 0)
    return True, temperature, target_temp, cooler_on, cooler_power

def check_focuser_status():
    """Check if the focuser is connected and get its position."""
    print(f"[{get_timestamp()}] Querying NINA for focuser status...")
    
    # Get focuser info
    focuser_data = query_nina_api(NINA_API_ENDPOINT_FOCUSER)
    if not focuser_data:
        print(f"[{get_timestamp()}] Cannot retrieve focuser data.")
        return False, None
    
    focuser_info = focuser_data.get("Response", {})
    if not focuser_info.get("Connected", False):
        print(f"[{get_timestamp()}] Focuser is not connected.")
        return False, None

    # Get position if available
    position = focuser_info.get("Position", None)
    return True, position

def check_mount_status():
    """Check if the mount is connected and get its position and status."""
    print(f"[{get_timestamp()}] Querying NINA for mount status...")
    
    # Get mount info
    mount_data = query_nina_api(NINA_API_ENDPOINT_MOUNT)
    if not mount_data:
        print(f"[{get_timestamp()}] Cannot retrieve mount data.")
        return False, None, None, False, False, False
    
    mount_info = mount_data.get("Response", {})
    if not mount_info.get("Connected", False):
        print(f"[{get_timestamp()}] Mount is not connected.")
        return False, None, None, False, False, False

    # Extract coordinates
    ra = mount_info.get("RightAscension", None)
    dec = mount_info.get("Declination", None)
    
    # Extract status flags
    at_park = mount_info.get("AtPark", False)
    at_home = mount_info.get("AtHome", False)
    slewing = mount_info.get("Slewing", False)
    
    return True, ra, dec, at_park, at_home, slewing

def check_dome_status():
    """Check if the dome is connected and get its shutter status."""
    print(f"[{get_timestamp()}] Querying NINA for dome status...")
    
    dome_data = query_nina_api(NINA_API_ENDPOINT_DOME)
    if not dome_data:
        print(f"[{get_timestamp()}] Cannot retrieve dome data.")
        return False, None
    
    dome_info = dome_data.get("Response", {})
    is_connected = dome_info.get("Connected", False)
    
    if not is_connected:
        print(f"[{get_timestamp()}] Dome is not connected.")
        return False, None
    
    # Get shutter status
    shutter_status = dome_info.get("ShutterStatus", None)
    return True, shutter_status

def check_filterwheel_status():
    """Check if the filter wheel is connected and get the selected filter name."""
    print(f"[{get_timestamp()}] Querying NINA for filter wheel status...")
    
    filterwheel_data = query_nina_api(NINA_API_ENDPOINT_FILTERWHEEL)
    if not filterwheel_data:
        print(f"[{get_timestamp()}] Cannot retrieve filter wheel data.")
        return False, None
    
    filterwheel_info = filterwheel_data.get("Response", {})
    is_connected = filterwheel_info.get("Connected", False)
    
    if not is_connected:
        print(f"[{get_timestamp()}] Filter wheel is not connected.")
        return False, None
    
    # Get selected filter information
    selected_filter = filterwheel_info.get("SelectedFilter", {})
    filter_name = selected_filter.get("Name", None)
    
    return True, filter_name

def check_guider_status():
    """Check if the guider is connected and get RMS error."""
    print(f"[{get_timestamp()}] Querying NINA for guider status...")
    
    guider_data = query_nina_api(NINA_API_ENDPOINT_GUIDER)
    if not guider_data:
        print(f"[{get_timestamp()}] Cannot retrieve guider data.")
        return False, None
    
    guider_info = guider_data.get("Response", {})
    is_connected = guider_info.get("Connected", False)
    
    if not is_connected:
        print(f"[{get_timestamp()}] Guider is not connected.")
        return False, None
    
    # Get RMS error information
    rms_error = None
    if "RMSError" in guider_info and "Total" in guider_info["RMSError"]:
        rms_error = guider_info["RMSError"]["Total"].get("Arcseconds", None)
    
    return True, rms_error

# MQTT settings
MQTT_BROKER = "192.168.1.49"  # Replace with your MQTT broker address
MQTT_PORT = 1883
MQTT_TOPIC = "obsybox/equipment"
MQTT_CLIENT_ID = "nina-monitor"

def publish_to_mqtt(data):
    try:
        # Create a flat JSON structure
        flat_json = {
            # Measurement name as a field
            "measurement": "telescope_equipment",
            
            # Camera data
            "camera_connected": 1 if data['camera']['connected'] else 0,
            "camera_temperature": data["camera"]["temperature"],
            "camera_target_temperature": data["camera"]["target_temperature"],
            "camera_cooler_on": 1 if data['camera']['cooler_on'] else 0,
            "camera_cooler_power": data["camera"]["cooler_power"],
            
            # Focuser data
            "focuser_connected": 1 if data['focuser']['connected'] else 0,
            "focuser_position": data["focuser"]["position"],
            
            # Mount data
            "mount_connected": 1 if data['mount']['connected'] else 0,
            "mount_ra": data["mount"]["ra"],
            "mount_dec": data["mount"]["dec"],
            "mount_at_park": 1 if data['mount']['at_park'] else 0,
            "mount_at_home": 1 if data['mount']['at_home'] else 0,
            "mount_slewing": 1 if data['mount']['slewing'] else 0,
            
            # Dome data
            "dome_connected": 1 if data['dome']['connected'] else 0,
            "dome_shutter_status": data["dome"]["shutter_status"],
            
            # Filterwheel data
            "filterwheel_connected": 1 if data['filterwheel']['connected'] else 0,
            "filterwheel_filter": data["filterwheel"]["selected_filter"],
            
            # Guider data
            "guider_connected": 1 if data['guider']['connected'] else 0,
            "guider_rms_error": data["guider"]["rms_error_arcsec"],
            
            # Timestamp (as string)
            "timestamp": get_timestamp()
        }
        
        # Remove None values
        flat_json = {k: v for k, v in flat_json.items() if v is not None}
        
        # Create MQTT client
        client = mqtt.Client(client_id=MQTT_CLIENT_ID, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # Convert to JSON string
        payload = json.dumps(flat_json)
        print(f"MQTT payload: {payload}")
        
        result = client.publish(MQTT_TOPIC, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[{get_timestamp()}] Successfully published to {MQTT_TOPIC}")
        else:
            print(f"[{get_timestamp()}] Failed to publish to MQTT: {result}")
            
        client.disconnect()
        return True
    except Exception as e:
        print(f"[{get_timestamp()}] MQTT error: {e}")
        return False

def main():
    print(f"[{get_timestamp()}] Starting NINA equipment monitoring...")
    print(f"[{get_timestamp()}] Using NINA API URL: {NINA_API_URL}")
    print(f"[{get_timestamp()}] Using MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"[{get_timestamp()}] Monitoring will update every 30 seconds. Press Ctrl+C to exit.")
    
    try:
        while True:  # Endless loop
            try:
                # Get camera status
                is_camera_connected, temperature, target_temp, cooler_on, cooler_power = check_camera_status()

                # Get focuser status
                is_focuser_connected, focuser_position = check_focuser_status()
                
                # Get mount status
                is_mount_connected, ra, dec, at_park, at_home, slewing = check_mount_status()
                
                # Get dome status
                is_dome_connected, shutter_status = check_dome_status()
                
                # Get filter wheel status
                is_filterwheel_connected, selected_filter = check_filterwheel_status()

                # Get guider status
                is_guider_connected, rms_error = check_guider_status()

                # Create results JSON
                result = {
                    "camera": {
                        "connected": is_camera_connected,
                        "temperature": temperature,
                        "target_temperature": target_temp,
                        "cooler_on": cooler_on,
                        "cooler_power": cooler_power
                    },
                    "focuser": {
                        "connected": is_focuser_connected,
                        "position": focuser_position
                    },
                    "mount": {
                        "connected": is_mount_connected,
                        "ra": ra,
                        "dec": dec,
                        "at_park": at_park,
                        "at_home": at_home,
                        "slewing": slewing
                    },
                    "dome": {
                        "connected": is_dome_connected,
                        "shutter_status": shutter_status
                    },
                    "filterwheel": {
                        "connected": is_filterwheel_connected,
                        "selected_filter": selected_filter
                    },
                    "guider": {
                        "connected": is_guider_connected,
                        "rms_error_arcsec": rms_error
                    },
                    "timestamp": get_timestamp()
                }
                
                # Print results locally
                print(f"\nResults summary: {json.dumps(result, indent=2)}")
                
                # Publish to MQTT
                mqtt_success = publish_to_mqtt(result)
                if mqtt_success:
                    print(f"[{get_timestamp()}] Data sent to MQTT topic {MQTT_TOPIC}")
                else:
                    print(f"[{get_timestamp()}] Failed to send data to MQTT")
                
                # Wait for 30 seconds before next update
                print(f"[{get_timestamp()}] Next update in 30 seconds...")
                time.sleep(30)
                
            except Exception as e:
                print(f"[{get_timestamp()}] Error in monitoring cycle: {e}")
                print(f"[{get_timestamp()}] Will try again in 30 seconds")
                time.sleep(30)  # Continue the loop even after errors
                
    except KeyboardInterrupt:
        print(f"[{get_timestamp()}] Monitoring stopped by user.")
        print(f"[{get_timestamp()}] Exiting...")

if __name__ == "__main__":
    main()