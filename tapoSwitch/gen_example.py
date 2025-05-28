"""Generic Device Example"""

import asyncio
import os

from tapo import ApiClient

# import the secrets
if os.path.exists("secrets.py"):
    from secrets import tapo_username, tapo_password, ip_address
else:
    tapo_username = "your_tapo_username"
    tapo_password = "your_tapo_password"
    ip_address = "your_device_ip_address"
    


async def main():
    """Main function to control the Tapo device."""
    print("Starting Tapo device control...")
    print(f"Using credentials: {tapo_username} at {ip_address}")
    # Create an instance of ApiClient with the provided credentials    
    client = ApiClient(tapo_username, tapo_password)
    device = await client.generic_device(ip_address)

    print("Turning device on...")
    await device.on()

    print("Waiting 20 seconds...")
    await asyncio.sleep(20)

    print("Turning device off...")
    await device.off()

    device_info = await device.get_device_info()
    print(f"Device info: {device_info.to_dict()}")


if __name__ == "__main__":
    asyncio.run(main())