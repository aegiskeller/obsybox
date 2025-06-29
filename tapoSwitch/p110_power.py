"""Query Tapo P110 devices and publish power usage to MQTT. Intended for use as a cron job."""

import os
import asyncio
from tapo import ApiClient
import paho.mqtt.client as mqtt
import time
import json

MQTT_BROKER = "192.168.1.49"  # Change to your MQTT broker address if needed
MQTT_PORT = 1883
MQTT_TOPIC = "obsybox/power_usage"

# import the secrets
if os.path.exists("secrets.py"):
    from secrets import tapo_username, tapo_password, tapo_p110_ips
else:
    tapo_username = "your_tapo_username"
    tapo_password = "your_tapo_password"
    tapo_p110_ips = ["192.168.1.102"] # this is the reserved ip for the tapo p110

async def get_power(ip, tapo_username, tapo_password):
    try:
        tapo_client = ApiClient(tapo_username, tapo_password)
        device = await tapo_client.p110(ip)
        energy = await device.get_energy_usage()
        power = energy.current_power
        print(f"Power usage for {ip}: {power} W")
        return {"ip": ip, "power": power, "timestamp": int(time.time())}
    except Exception as e:
        print(f"Failed to get power usage for {ip}: {e}")
        return None

async def main():
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return

    tasks = [get_power(ip, tapo_username, tapo_password) for ip in tapo_p110_ips]
    results = await asyncio.gather(*tasks)
    for payload in results:
        if payload is not None:
            client.publish(MQTT_TOPIC, json.dumps(payload))

    client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())