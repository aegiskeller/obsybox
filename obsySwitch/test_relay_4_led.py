#!/usr/bin/env python3
"""
Quick Relay 4 Test - Check if LED lights up
"""
import serial
import time

def test_relay_4_led():
    try:
        ser = serial.Serial('/dev/cu.usbserial-14120', 9600, timeout=2)
        time.sleep(2)
        
        print(f"Testing Relay 4 - Watch for LED on relay board!")
        print("=" * 50)
        
        for i in range(3):
            print(f"\n Test {i+1}/3 - Turning Relay 4 ON")
            ser.write(b'SET_RELAY,4,ON\n')
            time.sleep(1)
            
            print(f"Does Relay 4 LED light up? (Check the relay board)")
            time.sleep(2)
            
            print(f"Turning Relay 4 OFF")
            ser.write(b'SET_RELAY,4,OFF\n')
            time.sleep(1)
            
            print(f"Does Relay 4 LED turn off?")
            time.sleep(2)
        
        ser.close()
        
        print("\n Results Analysis:")
        print(f"If LED lights up: Physical relay is bad, jumpers OK")
        print(f"If NO LED: Check jumpers, compare to working relays")
        print(f"If LED stays on: Wrong trigger level jumper")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_relay_4_led()