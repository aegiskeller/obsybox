import psutil
import time
import json
import socket
import paho.mqtt.client as mqtt
import subprocess

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

def safe_value(val):
    return 0.0 if val is None else val

def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()

    while True:
        cpu_temp = safe_value(get_cpu_temp())
        cpu_load = safe_value(psutil.cpu_percent(interval=1))
        disk = psutil.disk_usage('C:\\')
        disk_free_gb = safe_value(round(disk.free / (1024 ** 3), 2))
        wifi_strength = safe_value(get_wifi_strength())

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