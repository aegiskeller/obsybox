"""Scan for Tapo P110 devices and report power usage."""

import asyncio
import os
from tapo import ApiClient

# import the secrets
if os.path.exists("secrets.py"):
    from secrets import tapo_username, tapo_password, tapo_p110_ips
else:
    tapo_username = "your_tapo_username"
    tapo_password = "your_tapo_password"
    tapo_p110_ips = ["192.168.1.100"]  # <-- Replace with your P110 IP(s)

async def main():
    print("Checking Tapo P110 devices for power usage...")
    for ip in tapo_p110_ips:
        print(f"Checking Tapo P110: {ip}")
        try:
            client = ApiClient(tapo_username, tapo_password)
            device = await client.p110(ip)
            energy = await device.get_energy_usage()
            print(f"Power usage for {ip}: {energy.current_power} W")
        except Exception as e:  # <-- Catch all exceptions
            print(f"Failed to get power usage for {ip}: {e}")

if __name__ == "__main__":
    asyncio.run(main())