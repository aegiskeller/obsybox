#!/usr/bin/env python3
"""
All Relays Diagnostic Tool

Test all 4 relays to verify wiring and functionality.
This will test each relay individually and then all together.
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

def test_all_relays():
    """Test all 4 relays systematically"""
    port = find_arduino()
    if not port:
        print("❌ Arduino not found")
        return
    
    print(f"🔌 Connecting to Arduino on {port}")
    
    try:
        ser = serial.Serial(port, 9600, timeout=3)
        time.sleep(2)  # Wait for Arduino boot
        ser.reset_input_buffer()
        
        print("\n🧪 ALL RELAYS DIAGNOSTIC TEST")
        print("=" * 50)
        
        # Get initial status
        print("1️⃣ Getting initial status of all relays...")
        ser.write(b"GET_STATUS\n")
        time.sleep(1)
        
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and line.startswith('STATUS,'):
                print(f"   {line}")
        
        # Test each relay individually
        relay_info = [
            (1, "Mount", "Pin 2"),
            (2, "Camera", "Pin 3"),
            (3, "Focuser", "Pin 4"),
            (4, "Aux", "Pin 5")
        ]
        
        print(f"\n2️⃣ Testing each relay individually...")
        print("   🔊 Listen carefully for click sounds from each relay!")
        
        for relay_num, relay_name, pin_info in relay_info:
            print(f"\n   ⚡ Testing Relay {relay_num} ({relay_name} - {pin_info})")
            
            # Turn ON
            print(f"      Turning ON...")
            ser.reset_input_buffer()
            ser.write(f"SET_RELAY,{relay_num},ON\n".encode())
            time.sleep(0.5)
            
            # Read response
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('#') and 'Relay' in line:
                    print(f"      Arduino: {line}")
                elif line.startswith('OK,'):
                    print(f"      Response: {line}")
            
            # Ask user
            heard_click = input(f"      Did you hear a CLICK from Relay {relay_num}? (y/n): ").lower().strip()
            if heard_click == 'y':
                print(f"      ✅ Relay {relay_num} ({relay_name}) is working!")
            else:
                print(f"      ❌ Relay {relay_num} ({relay_name}) - no click detected")
            
            # Turn OFF
            print(f"      Turning OFF...")
            ser.write(f"SET_RELAY,{relay_num},OFF\n".encode())
            time.sleep(0.5)
            
            # Read response
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('#') and 'Relay' in line:
                    print(f"      Arduino: {line}")
            
            time.sleep(1)  # Pause between relays
        
        print(f"\n3️⃣ Testing all relays together...")
        print("   This will turn ON all relays in sequence, then OFF")
        
        # Turn all ON in sequence
        print("   Turning all relays ON...")
        for relay_num, relay_name, _ in relay_info:
            ser.write(f"SET_RELAY,{relay_num},ON\n".encode())
            time.sleep(0.3)
            print(f"      Relay {relay_num} ({relay_name}) ON")
        
        time.sleep(2)
        
        # Turn all OFF with emergency stop
        print("   Emergency stop - turning all OFF...")
        ser.write(b"EMERGENCY_STOP\n")
        time.sleep(1)
        
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('#'):
                print(f"   Arduino: {line}")
        
        print(f"\n4️⃣ Final status check...")
        ser.write(b"GET_STATUS\n")
        time.sleep(1)
        
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and line.startswith('STATUS,'):
                print(f"   Final status: {line}")
        
        ser.close()
        
        print(f"\n📋 WIRING VERIFICATION CHECKLIST")
        print("=" * 50)
        print("For each relay that's working:")
        print("  ✅ Power: VCC → Arduino 5V, GND → Arduino GND")
        print("  ✅ Signals:")
        print("     • IN1 → Arduino Pin 2 (Relay 1 - Mount)")
        print("     • IN2 → Arduino Pin 3 (Relay 2 - Camera)")  
        print("     • IN3 → Arduino Pin 4 (Relay 3 - Focuser)")
        print("     • IN4 → Arduino Pin 5 (Relay 4 - Aux)")
        
        print(f"\n🔧 If any relays aren't clicking:")
        print("  1. Check signal wire connections")
        print("  2. Verify relay module power")
        print("  3. Look for LED indicators on relay module")
        print("  4. Some modules need external 5V supply")
        print("  5. Check if jumper caps are properly positioned")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_rapid_switching():
    """Test rapid switching of all relays"""
    port = find_arduino()
    if not port:
        print("❌ Arduino not found")
        return
    
    print(f"🔌 Connecting to Arduino for rapid switching test...")
    
    try:
        ser = serial.Serial(port, 9600, timeout=3)
        time.sleep(2)
        ser.reset_input_buffer()
        
        print(f"\n⚡ RAPID SWITCHING TEST")
        print("=" * 30)
        print("This will rapidly switch all relays - should hear lots of clicks!")
        
        input("Press Enter when ready to start rapid test...")
        
        # Rapid switching sequence
        for cycle in range(3):
            print(f"Cycle {cycle + 1}/3...")
            
            # Turn all on quickly
            for relay_num in range(1, 5):
                ser.write(f"SET_RELAY,{relay_num},ON\n".encode())
                time.sleep(0.1)
            
            time.sleep(0.5)
            
            # Turn all off quickly  
            for relay_num in range(1, 5):
                ser.write(f"SET_RELAY,{relay_num},OFF\n".encode())
                time.sleep(0.1)
            
            time.sleep(0.5)
        
        # Final cleanup
        ser.write(b"EMERGENCY_STOP\n")
        print("Done! All relays should be OFF now.")
        
        ser.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 ObsyBox 4-Relay Test Suite")
    print("=" * 40)
    print("1. Comprehensive test")
    print("2. Rapid switching test")
    choice = input("Choose test (1/2): ").strip()
    
    if choice == "1":
        test_all_relays()
    elif choice == "2":
        test_rapid_switching()
    else:
        print("Running comprehensive test...")
        test_all_relays()