import time
import json
import paho.mqtt.client as mqtt
import requests
import socket

MQTT_BROKER = "192.168.1.49"
MQTT_TOPIC = "obsybox/system_monitoring"
INTERVAL = 60  # seconds
LHM_SERVER_URL = "http://localhost:8085/data.json"

def get_cpu_temp():
    try:
        response = requests.get(LHM_SERVER_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Try to find CPU temperature as before
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
            # If no CPU temperature found, print all available temperature sensors for debugging
            print("No CPU temperature found. Available temperature sensors:")
            for hardware in data.get("Children", []):
                hw_name = hardware.get("Text", "")
                for sensor_group in hardware.get("Children", []):
                    if "temperature" in sensor_group.get("Text", "").lower():
                        for sensor in sensor_group.get("Children", []):
                            sensor_name = sensor.get("Text", "")
                            sensor_value = sensor.get("Value", "")
                            print(f"{hw_name} > {sensor_name}: {sensor_value}")
    except Exception as e:
        print(f"Error getting CPU temperature: {e}")
    return None

def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
    while True:
        cpu_temp = get_cpu_temp()
        payload = {
            "cpu_temp": cpu_temp,
            "hostname": socket.gethostname()
        }
        if client.is_connected():
            client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
            print("Published:", payload)
        else:
            print("MQTT not connected, skipping publish.")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()