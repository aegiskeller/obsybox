#!/usr/bin/env python3
"""
Simple Arduino Serial Test

Test basic communication with Arduino to debug connection issues.
"""

import serial
import time
import serial.tools.list_ports

def find_arduino_port():
    """Find Arduino port"""
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'ftdi', 'cp210', 'usb']):
            print(f"Found Arduino: {port.device} - {port.description}")
            return port.device
    
    return None

def test_arduino_communication():
    """Test basic Arduino communication"""
    port = find_arduino_port()
    
    if not port:
        print(f"No Arduino found")
        return
    
    print(f"Connecting to {port}")
    
    try:
        # Open serial connection
        ser = serial.Serial(port, 9600, timeout=5)
        
        # Wait for Arduino to boot
        print(f"Waiting for Arduino to initialize...")
        time.sleep(3)
        
        # Clear buffer
        ser.reset_input_buffer()
        
        print("\n Reading raw Arduino output for 10 seconds...")
        print("-" * 50)
        
        start_time = time.time()
        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"Arduino: {line}")
                except Exception as e:
                    print(f"Error reading: {e}")
            
            time.sleep(0.1)
        
        print("-" * 50)
        
        # Test sending commands
        print("\nTesting commands...")
        
        commands = ["PING", "GET_STATUS", "GET_RELAY,1"]
        
        for cmd in commands:
            print(f"\n>>> Sending: {cmd}")
            ser.reset_input_buffer()
            ser.write((cmd + '\n').encode('utf-8'))
            ser.flush()
            
            # Wait for response
            time.sleep(1)
            
            response_count = 0
            while ser.in_waiting > 0 and response_count < 10:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"<<< Response: {line}")
                        response_count += 1
                except Exception as e:
                    print(f"Error: {e}")
                    break
            
            if response_count == 0:
                print("<<< No response")
        
        ser.close()
        print("\n Test completed")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_arduino_communication()