"""Query Tapo P110 devices and publish power usage to MQTT. Intended for use as a cron job."""

import os
from tapo import ApiClient
import paho.mqtt.client as mqtt
import time

MQTT_BROKER = "192.168.1.49"  # Change to your MQTT broker address if needed
MQTT_PORT = 1883
MQTT_TOPIC = "obsybox/power_usage"

# import the secrets
if os.path.exists("secrets.py"):
    from secrets import tapo_username, tapo_password, tapo_p110_ips
else:
    tapo_username = "your_tapo_username"
    tapo_password = "your_tapo_password"
    tapo_p110_ips = ["192.168.1.34"]

def main():
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return

    for ip in tapo_p110_ips:
        print(f"Checking Tapo P110: {ip}")
        try:
            tapo_client = ApiClient(tapo_username, tapo_password)
            device = tapo_client.p110(ip)
            energy = device.get_energy_usage()
            # If using python-tapo >=3.0, these may be coroutines; if so, use asyncio.run() or await
            if hasattr(energy, "current_power"):
                power = energy.current_power
            elif isinstance(energy, dict) and "current_power" in energy:
                power = energy["current_power"]
            else:
                power = None
            print(f"Power usage for {ip}: {power} W")
            payload = {
                "ip": ip,
                "power": power,
                "timestamp": int(time.time())
            }
            client.publish(MQTT_TOPIC, str(payload))
        except Exception as e:
            print(f"Failed to get power usage for {ip}: {e}")

    client.disconnect()

if __name__ == "__main__":
    main()