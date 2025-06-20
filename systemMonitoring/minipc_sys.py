import psutil
import time
import json
import socket
import paho.mqtt.client as mqtt
import subprocess

### This script monitors system metrics on a Windows machine and publishes them to an MQTT broker.
# It retrieves CPU temperature, CPU load, disk space, hostname, and Wi-Fi signal strength.
# Ensure you have the required libraries installed:
# pip install psutil paho-mqtt wmi
# Usage:
# 1. Install the required libraries:    
#    pip install psutil paho-mqtt wmi
# 2. Ensure you have the WMI library available for Windows.
# 3. Update the MQTT_BROKER variable with your MQTT broker's IP address.
# 4. Run the script:
#    python minipc_sys.py

try:
    import wmi
    w = wmi.WMI(namespace="root\\wmi")
except ImportError:
    w = None

MQTT_BROKER = "192.168.1.49"
MQTT_TOPIC = "obsybox/system_monitoring"
INTERVAL = 60  # seconds

def get_cpu_temp():
    if w:
        try:
            temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
            # Convert from tenths of Kelvin to Celsius
            temp_c = float(temperature_info.CurrentTemperature) / 10.0 - 273.15
            return round(temp_c, 1)
        except Exception:
            return None
    return None

def get_wifi_strength():
    try:
        output = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'], encoding='utf-8')
        for line in output.split('\n'):
            if 'Signal' in line:
                # Example line: '    Signal                   : 88%'
                return int(line.split(':')[1].strip().replace('%',''))
    except Exception:
        return None

def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()

    while True:
        cpu_temp = get_cpu_temp()
        cpu_load = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('C:\\')
        disk_free_gb = round(disk.free / (1024 ** 3), 2)
        wifi_strength = get_wifi_strength()

        payload = {
            "cpu_temp": cpu_temp,
            "cpu_load": cpu_load,
            "disk_free_gb": disk_free_gb,
            "hostname": socket.gethostname(),
            "wifi_strength": wifi_strength
        }

        client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        print("Published:", payload)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()