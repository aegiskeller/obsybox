"""Scan for Tapo P110 devices and report power usage to MQTT every 30 seconds."""

import asyncio
import os
from tapo import ApiClient
import paho.mqtt.client as mqtt
import time

MQTT_BROKER = "localhost"  # Change to your MQTT broker address if needed
MQTT_PORT = 1883
MQTT_TOPIC = "obsybox/power_usage"

# import the secrets
if os.path.exists("secrets.py"):
    from secrets import tapo_username, tapo_password, tapo_p110_ips
else:
    tapo_username = "your_tapo_username"
    tapo_password = "your_tapo_password"
    tapo_p110_ips = ["192.168.1.34"]  
async def main():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    print("Checking Tapo P110 devices for power usage every 30 seconds...")
    while True:
        for ip in tapo_p110_ips:
            print(f"Checking Tapo P110: {ip}")
            try:
                tapo_client = ApiClient(tapo_username, tapo_password)
                device = await tapo_client.p110(ip)
                energy = await device.get_energy_usage()
                print(f"Power usage for {ip}: {energy.current_power} W")
                payload = {
                    "ip": ip,
                    "power": energy.current_power,
                    "timestamp": int(time.time())
                }
                client.publish(MQTT_TOPIC, str(payload))
            except Exception as e:
                print(f"Failed to get power usage for {ip}: {e}")
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())