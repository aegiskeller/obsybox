#!/usr/bin/env python3
"""
Test script for ObsyBox Relay Controller

This script demonstrates basic functionality and can be used to verify
that the relay controller is working correctly.

Usage:
    python test_relay_controller.py
    
Requirements:
    - Arduino relay controller running and connected to network
    - Python requests library
"""

import sys
import time
import json
from obsyswitch_driver import ObsySwitchController, ASCOMSwitchV2

def test_basic_connectivity():
    """Test basic connectivity to the relay controller"""
    print("=" * 50)
    print("TESTING BASIC CONNECTIVITY")
    print("=" * 50)
    
    controller = ObsySwitchController()
    
    print(f"Attempting to connect to {controller.ip_address}...")
    
    if controller.connect():
        print("✓ Connection successful!")
        
        device_info = controller.get_device_info()
        if device_info:
            print(f"✓ Device Name: {device_info.device_name}")
            print(f"✓ Firmware: {device_info.firmware}")
            print(f"✓ Build Date: {device_info.build_date}")
            print(f"✓ IP Address: {device_info.ip}")
            print(f"✓ WiFi RSSI: {device_info.rssi} dBm")
            print(f"✓ Uptime: {controller.get_uptime()} seconds")
            print(f"✓ Available switches: {device_info.max_switch + 1}")
        
        controller.disconnect()
        return True
    else:
        print("✗ Connection failed!")
        print("  Check that:")
        print("  - Arduino is powered on and running")
        print("  - Device is connected to WiFi")
        print("  - IP address is correct (192.168.1.75)")
        print("  - No firewall blocking access")
        return False

def test_switch_control():
    """Test individual switch control"""
    print("\n" + "=" * 50)
    print("TESTING SWITCH CONTROL")
    print("=" * 50)
    
    controller = ObsySwitchController()
    
    if not controller.connect():
        print("✗ Cannot connect to device for switch testing")
        return False
    
    try:
        # Test each switch
        for switch_id in range(controller.get_max_switch() + 1):
            switch_name = controller.get_switch_name(switch_id)
            print(f"\nTesting Switch {switch_id} ({switch_name}):")
            
            # Get initial state
            initial_state = controller.get_switch(switch_id)
            print(f"  Initial state: {'ON' if initial_state else 'OFF'}")
            
            # Turn on
            print("  Turning ON...")
            if controller.set_switch(switch_id, True):
                time.sleep(0.5)
                state = controller.get_switch(switch_id)
                if state:
                    print("  ✓ Successfully turned ON")
                else:
                    print("  ✗ Failed to turn ON (state mismatch)")
            else:
                print("  ✗ Failed to send ON command")
            
            # Turn off
            print("  Turning OFF...")
            if controller.set_switch(switch_id, False):
                time.sleep(0.5)
                state = controller.get_switch(switch_id)
                if not state:
                    print("  ✓ Successfully turned OFF")
                else:
                    print("  ✗ Failed to turn OFF (state mismatch)")
            else:
                print("  ✗ Failed to send OFF command")
            
            # Test toggle
            print("  Testing toggle...")
            if controller.toggle_switch(switch_id):
                time.sleep(0.5)
                print("  ✓ Toggle command successful")
                
                # Toggle back to original state
                controller.set_switch(switch_id, initial_state)
                time.sleep(0.5)
            else:
                print("  ✗ Toggle command failed")
        
        # Test getting all switches
        print(f"\nAll switch states: {controller.get_all_switches()}")
        
        controller.disconnect()
        return True
        
    except Exception as e:
        print(f"✗ Error during switch testing: {str(e)}")
        controller.disconnect()
        return False

def test_ascom_interface():
    """Test ASCOM interface wrapper"""
    print("\n" + "=" * 50)
    print("TESTING ASCOM INTERFACE")
    print("=" * 50)
    
    ascom = ASCOMSwitchV2()
    
    print("Connecting via ASCOM interface...")
    ascom.Connected = True
    
    if ascom.Connected:
        print("✓ ASCOM interface connected")
        
        driver_info = ascom.GetDriverInfo()
        print(f"✓ Driver: {driver_info['Name']}")
        print(f"✓ Version: {driver_info['DriverVersion']}")
        
        max_switch = ascom.MaxSwitch
        print(f"✓ Max switch index: {max_switch}")
        
        # Test ASCOM methods
        for i in range(max_switch + 1):
            switch_name = ascom.GetSwitchName(i)
            can_write = ascom.CanWrite(i)
            current_state = ascom.GetSwitch(i)
            
            print(f"  Switch {i}: {switch_name} ({'R/W' if can_write else 'R/O'}) = {'ON' if current_state else 'OFF'}")
        
        # Test setting a switch via ASCOM
        if max_switch >= 0:
            print(f"\nTesting ASCOM SetSwitch on switch 0...")
            original_state = ascom.GetSwitch(0)
            
            ascom.SetSwitch(0, not original_state)
            time.sleep(0.5)
            new_state = ascom.GetSwitch(0)
            
            if new_state != original_state:
                print("✓ ASCOM SetSwitch working")
                
                # Restore original state
                ascom.SetSwitch(0, original_state)
                time.sleep(0.5)
            else:
                print("✗ ASCOM SetSwitch not working")
        
        ascom.Connected = False
        return True
    else:
        print("✗ ASCOM interface connection failed")
        return False

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n" + "=" * 50)
    print("TESTING ERROR HANDLING")
    print("=" * 50)
    
    controller = ObsySwitchController()
    
    # Test invalid switch IDs
    print("Testing invalid switch IDs...")
    try:
        result = controller.get_switch(-1)
        print("✗ Should have failed with negative switch ID")
    except ValueError:
        print("✓ Correctly rejected negative switch ID")
    
    try:
        result = controller.get_switch(999)
        print("✗ Should have failed with high switch ID")
    except ValueError:
        print("✓ Correctly rejected invalid switch ID")
    
    # Test disconnected operations
    print("Testing operations while disconnected...")
    if not controller.set_switch(0, True):
        print("✓ Correctly failed to set switch when disconnected")
    else:
        print("✗ Should have failed when disconnected")
    
    return True

def test_performance():
    """Test performance and timing"""
    print("\n" + "=" * 50)
    print("TESTING PERFORMANCE")
    print("=" * 50)
    
    controller = ObsySwitchController()
    
    if not controller.connect():
        print("✗ Cannot connect for performance testing")
        return False
    
    # Test response times
    num_tests = 10
    print(f"Testing response times ({num_tests} iterations)...")
    
    times = []
    for i in range(num_tests):
        start_time = time.time()
        controller.get_switch(0)
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    min_time = min(times)
    
    print(f"✓ Average response time: {avg_time:.3f}s")
    print(f"✓ Min response time: {min_time:.3f}s")
    print(f"✓ Max response time: {max_time:.3f}s")
    
    if avg_time < 1.0:
        print("✓ Performance acceptable")
    else:
        print("⚠ Performance may be slow")
    
    controller.disconnect()
    return True

def main():
    """Run all tests"""
    print("ObsyBox Relay Controller Test Suite")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Basic Connectivity", test_basic_connectivity),
        ("Switch Control", test_switch_control),
        ("ASCOM Interface", test_ascom_interface),
        ("Error Handling", test_error_handling),
        ("Performance", test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            success = test_func()
            results.append((test_name, success))
            if success:
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:<20} : {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Relay controller is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())