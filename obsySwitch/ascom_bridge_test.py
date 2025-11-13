#!/usr/bin/env python3
"""
ASCOM Bridge Test Script

Test the ASCOM-compatible interface for your relay controller.
This demonstrates how to use the ASCOM driver programmatically.
"""

import sys
import time
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from obsyswitch_serial_driver import ASCOMSwitchSerial
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure obsyswitch_serial_driver.py is in the same directory")
    sys.exit(1)

def test_ascom_interface():
    """Test the ASCOM interface"""
    print(f"Testing ASCOM Interface for ObsyBox Relay Controller")
    print("=" * 60)
    
    # Create ASCOM-compatible driver instance
    ascom_switch = ASCOMSwitchSerial()
    
    try:
        # Connect to Arduino
        print(f"Connecting to relay controller...")
        ascom_switch.Connected = True
        
        if ascom_switch.Connected:
            print(f"Connected to Arduino relay controller")
            
            # Get device information
            controller = ascom_switch.controller
            if controller.device_status:
                print(f"Device: {controller.device_status.device_name}")
                print(f"Firmware: {controller.device_status.firmware}")
                print(f"Free RAM: {controller.device_status.free_memory} bytes")
            
            print(f"Available switches: {ascom_switch.MaxSwitch + 1}")
            
            # Show current switch states
            print(f"\nCurrent Switch States:")
            for i in range(ascom_switch.MaxSwitch + 1):
                name = ascom_switch.GetSwitchName(i)
                state = ascom_switch.GetSwitch(i)
                can_write = ascom_switch.CanWrite(i)
                status_icon = "" if state else ""
                write_status = "" if can_write else ""
                print(f"  {status_icon} Switch {i}: {name} ({'ON' if state else 'OFF'}) {write_status}")
            
            # Test switch control
            print(f"\nTesting ASCOM Switch Control...")
            
            # Test Mount (Switch 0)
            print(f"\nTesting Mount (Switch 0)...")
            original_state = ascom_switch.GetSwitch(0)
            print(f"  Original state: {'ON' if original_state else 'OFF'}")
            
            # Turn on Mount
            print(f"  Setting Mount to ON...")
            ascom_switch.SetSwitch(0, True)
            time.sleep(1)
            
            new_state = ascom_switch.GetSwitch(0)
            print(f"  New state: {'ON' if new_state else 'OFF'}")
            
            if new_state:
                print(f"   Mount switch control working!")
            else:
                print(f"   Mount switch control failed")
            
            # Turn off Mount
            print(f"  Setting Mount to OFF...")
            ascom_switch.SetSwitch(0, False)
            time.sleep(1)
            
            final_state = ascom_switch.GetSwitch(0)
            print(f"  Final state: {'ON' if final_state else 'OFF'}")
            
            # Test Camera (Switch 1) 
            print(f"\nTesting Camera (Switch 1)...")
            print(f"  Turning Camera ON for 3 seconds...")
            ascom_switch.SetSwitch(1, True)
            time.sleep(3)
            print(f"  Turning Camera OFF...")
            ascom_switch.SetSwitch(1, False)
            
            # Test Focuser (Switch 2)
            print(f"\nTesting Focuser (Switch 2)...")
            print(f"  Turning Focuser ON for 2 seconds...")
            ascom_switch.SetSwitch(2, True)
            time.sleep(2)
            print(f"  Turning Focuser OFF...")
            ascom_switch.SetSwitch(2, False)
            
            # Show final states
            print(f"\nFinal Switch States:")
            for i in range(ascom_switch.MaxSwitch + 1):
                name = ascom_switch.GetSwitchName(i)
                state = ascom_switch.GetSwitch(i)
                status_icon = "" if state else ""
                print(f"  {status_icon} Switch {i}: {name} ({'ON' if state else 'OFF'})")
            
            print(f"\nASCOM interface test completed successfully!")
            
        else:
            print(f"Failed to connect to Arduino")
            print("Check:")
            print(f" - Arduino is connected via USB")
            print(f" - RelayController_Serial sketch is uploaded")
            print(f" - No other programs using the serial port")
            return False
            
    except Exception as e:
        print(f"ASCOM test failed: {str(e)}")
        return False
        
    finally:
        # Always disconnect
        if ascom_switch.Connected:
            ascom_switch.Connected = False
            print(f"Disconnected from Arduino")
    
    return True

def demonstrate_nina_integration():
    """Demonstrate how this integrates with NINA"""
    print(f"\nNINA Integration Examples")
    print("=" * 40)
    
    print(f"NINA External Script Configuration:")
    print(f"  Program: python3")
    print(f"  Arguments: /full/path/to/nina_serial_integration.py startup")
    print(f"  Working Dir: /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch")
    
    print(f"\nNINA Sequence Structure:")
    print(f"  Sequence Start:")
    print(f"   External Script: Observatory Startup")
    print(f"   Cool Camera")
    print(f"   Slew to Target") 
    print(f"   Auto Focus")
    print(f"   Start Imaging")
    print(f"  ")
    print(f"  Sequence End:")
    print(f"   Stop Imaging")
    print(f"   Warm Camera")
    print(f"   External Script: Observatory Shutdown")
    
    print(f"\nManual Control Commands:")
    print(f"  python nina_serial_integration.py startup   # Power on sequence")
    print(f"  python nina_serial_integration.py status    # Check equipment")
    print(f"  python nina_serial_integration.py shutdown  # Emergency stop")
    print(f"  python nina_serial_integration.py toggle 0  # Toggle mount")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Test ASCOM interface")
    print("2. Show NINA integration info")
    print("3. Both")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1" or choice == "3":
        success = test_ascom_interface()
        
    if choice == "2" or choice == "3":
        demonstrate_nina_integration()
        
    if choice not in ["1", "2", "3"]:
        print("Running full test...")
        test_ascom_interface()
        demonstrate_nina_integration()