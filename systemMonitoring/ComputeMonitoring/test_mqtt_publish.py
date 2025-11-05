#!/usr/bin/env python3
"""Simple MQTT test publisher."""

import json
from datetime import datetime

def test_publish():
    try:
        import paho.mqtt.publish as publish
        
        test_data = {
            "hostname": "Piglet-TEST",
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        payload = json.dumps(test_data)
        
        print(f"Publishing test message to obsybox/system_monitoring:")
        print(f"Payload: {payload}")
        
        publish.single('obsybox/system_monitoring', payload, hostname='192.168.1.49', qos=1)
        print("✅ Test message published successfully!")
        
    except Exception as e:
        print(f"❌ Error publishing test message: {e}")

if __name__ == "__main__":
    test_publish()