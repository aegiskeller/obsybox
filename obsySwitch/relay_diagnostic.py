#!/usr/bin/env python3
"""
Relay Diagnostic Tool

Test relay switching with direct Arduino commands to diagnose relay issues.
This will help determine if the relay is:
1. Wired correctly
2. Configured for active HIGH vs active LOW
3. Actually switching
"""

import serial
import time
import serial.tools.list_ports

def find_arduino():
    """Find Arduino port"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'ftdi', 'cp210', 'usb']):
            return port.device
    return None

def test_relay_switching():
    """Test relay switching with diagnostics"""
    port = find_arduino()
    if not port:
        print("❌ Arduino not found")
        return
    
    print(f"🔌 Connecting to Arduino on {port}")
    
    try:
        ser = serial.Serial(port, 9600, timeout=3)
        time.sleep(2)  # Wait for Arduino boot
        
        # Clear buffer
        ser.reset_input_buffer()
        
        print("\n🧪 RELAY DIAGNOSTIC TEST")
        print("=" * 40)
        
        # Get initial status
        print("1️⃣ Getting initial relay status...")
        ser.write(b"GET_STATUS\n")
        time.sleep(1)
        
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and not line.startswith('#'):
                print(f"   Status: {line}")
        
        print(f"\n2️⃣ Testing Relay 1 (Pin 2) - Listen for click sounds!")
        print("   Make sure you can hear the relay module...")
        
        # Test sequence
        test_cycles = [
            ("Turn ON", "SET_RELAY,1,ON"),
            ("Turn OFF", "SET_RELAY,1,OFF"),
            ("Turn ON again", "SET_RELAY,1,ON"),
            ("Turn OFF again", "SET_RELAY,1,OFF"),
        ]
        
        for step, command in test_cycles:
            print(f"\n   {step}...")
            ser.reset_input_buffer()
            ser.write((command + '\n').encode())
            ser.flush()
            
            # Wait and listen for response
            time.sleep(0.5)
            
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    if line.startswith('#'):
                        print(f"   Arduino: {line}")
                    else:
                        print(f"   Response: {line}")
            
            # Ask user if they heard the relay
            user_input = input(f"   Did you hear a CLICK from the relay? (y/n/q): ").lower().strip()
            if user_input == 'q':
                break
            elif user_input == 'y':
                print("   ✅ Relay is switching!")
            elif user_input == 'n':
                print("   ❌ No sound detected")
            else:
                print("   ⚠️  Please answer y/n/q")
            
            time.sleep(1)
        
        print(f"\n3️⃣ Testing rapid switching (should hear multiple clicks)...")
        for i in range(5):
            ser.write(b"SET_RELAY,1,TOGGLE\n")
            time.sleep(0.3)
            
            # Read response
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and line.startswith('#'):
                    print(f"   {line}")
        
        print(f"\n4️⃣ Final status check...")
        ser.write(b"GET_RELAY,1\n")
        time.sleep(1)
        
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and not line.startswith('#'):
                print(f"   Final state: {line}")
        
        ser.close()
        
        print(f"\n🔍 TROUBLESHOOTING GUIDE")
        print("=" * 40)
        print("If you heard clicks:")
        print("  ✅ Relay is working correctly!")
        print("  ✅ Wiring is good")
        print("  ✅ Arduino code is working")
        
        print(f"\nIf you heard NO clicks:")
        print("  🔧 Check these items:")
        print("  1. Relay module power: VCC to Arduino 5V, GND to Arduino GND")
        print("  2. Signal wire: IN1 connected to Arduino pin 2")
        print("  3. Relay module type: Try changing active HIGH/LOW setting")
        print("  4. Power supply: Some relay modules need external 5V power")
        print("  5. Relay module LED: Should light up when activated")
        
        print(f"\n💡 NEXT STEPS:")
        print("  - If relay clicks: System is working correctly!")
        print("  - If no clicks: Check wiring and power")
        print("  - If LED lights but no click: Relay may need external power")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_relay_switching()