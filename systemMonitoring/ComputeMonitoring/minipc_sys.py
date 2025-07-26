# Test for LHM
# reach out to the LHM server and get CPU temperature data
import json
import requests
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect('192.168.1.49', 1883, 60)

LHM_SERVER_URL = "http://localhost:8085/data.json"
response = requests.get(LHM_SERVER_URL)
cpu_temp = None

def find_sensor_value(node, target_path, value_type=None):
    """
    Recursively search for a sensor value by path.
    target_path: list of strings representing the hierarchy, e.g. ["KINGSTON SA400S37480G", "Load", "Used Space"]
    value_type: 'percent', 'celsius', 'kbps', etc. (optional, for parsing)
    """
    if isinstance(node, dict):
        if len(target_path) == 1 and node.get("Text", "") == target_path[0]:
            value = node.get("Value", "")
            if value:
                if value_type == 'percent' and '%' in value:
                    try:
                        return float(value.replace('%', '').strip())
                    except ValueError:
                        return None
                elif value_type == 'celsius' and '°C' in value:
                    try:
                        return float(value.replace('°C', '').strip())
                    except ValueError:
                        return None
                elif value_type == 'kbps' and 'KB/s' in value:
                    try:
                        return float(value.replace('KB/s', '').strip())
                    except ValueError:
                        return None
                else:
                    return value
        elif node.get("Text", "") == target_path[0]:
            for child in node.get("Children", []):
                result = find_sensor_value(child, target_path[1:], value_type)
                if result is not None:
                    return result
        else:
            for child in node.get("Children", []):
                result = find_sensor_value(child, target_path, value_type)
                if result is not None:
                    return result
    elif isinstance(node, list):
        for item in node:
            result = find_sensor_value(item, target_path, value_type)
            if result is not None:
                return result
    return None

if response.status_code == 200:
    data = response.json()
    cpu_temp = find_sensor_value(data, ["CPU Package"], value_type='celsius')
    ssd_used_space = find_sensor_value(data, ["KINGSTON SA400S37480G", "Load", "Used Space"], value_type='percent')
    wifi_util = find_sensor_value(data, ["Wi-Fi", "Load", "Network Utilization"], value_type='percent')
    wifi_upload = find_sensor_value(data, ["Wi-Fi", "Throughput", "Upload Speed"], value_type='kbps')

    payload = {}
    if cpu_temp is not None:
        payload["cpu_temp"] = cpu_temp
    if ssd_used_space is not None:
        payload["ssd_used_space"] = ssd_used_space
    if wifi_util is not None:
        payload["wifi_utilization"] = wifi_util
    if wifi_upload is not None:
        payload["wifi_upload_kbps"] = wifi_upload

    if payload:
        client.publish("obsybox/system_monitoring/piglet", json.dumps(payload), qos=1)
        print(f"Published payload: {payload}")
    else:
        print("No relevant sensor data found in LHM data.")
else:
    print(f"Failed to retrieve LHM data: {response.status_code}")