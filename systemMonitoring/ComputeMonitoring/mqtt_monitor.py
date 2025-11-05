#!/usr/bin/env python3
"""Simple MQTT subscriber to monitor obsybox/system_monitoring messages."""

import json
import time
from datetime import datetime

def monitor_mqtt():
    print("Trying to monitor MQTT messages on obsybox/system_monitoring...")
    print("MQTT Broker: 192.168.1.49:1883")
    print("Press Ctrl+C to stop\n")
    
    try:
        import paho.mqtt.client as mqtt
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print(f"✅ Connected to MQTT broker at 192.168.1.49")
                client.subscribe("obsybox/system_monitoring")
                print("📡 Subscribed to: obsybox/system_monitoring\n")
            else:
                print(f"❌ Failed to connect to MQTT broker. Return code: {rc}")
        
        def on_message(client, userdata, msg):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                # Try to parse as JSON for pretty printing
                data = json.loads(msg.payload.decode())
                print(f"[{timestamp}] 📊 System Stats:")
                for key, value in data.items():
                    print(f"  • {key}: {value}")
                print()
            except json.JSONDecodeError:
                print(f"[{timestamp}] Raw message: {msg.payload.decode()}")
                print()
        
        def on_disconnect(client, userdata, rc):
            print(f"🔌 Disconnected from MQTT broker")
        
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        
        # Try to connect
        client.connect("192.168.1.49", 1883, 60)
        
        # Start the loop
        client.loop_forever()
        
    except ImportError:
        print("❌ paho-mqtt not available. Install with: pip install paho-mqtt")
        return False
    except Exception as e:
        print(f"❌ Error connecting to MQTT broker: {e}")
        return False

if __name__ == "__main__":
    try:
        monitor_mqtt()
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")