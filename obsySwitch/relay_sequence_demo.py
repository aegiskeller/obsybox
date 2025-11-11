#!/usr/bin/env python3
"""
ObsyBox Relay Sequence Demo
Fun demonstration of all 4 relays turning on and off in sequence
"""

import time
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from obsyswitch_serial_driver import ObsySwitchSerialController

def relay_sequence_demo():
    """Run a fun relay sequence demonstration"""
    
    print("🎮 ObsyBox Relay Sequence Demo")
    print("=" * 50)
    
    # Connect to Arduino
    print("🔍 Connecting to Arduino...")
    controller = ObsySwitchSerialController()
    
    if not controller.connect():
        print("❌ Arduino not found - check USB connection")
        return False
    
    # Get device info
    info = controller.get_device_info()
    print(f"✅ Connected to: {info.device_name} v{info.firmware}")
    print(f"   Port: {controller.port}")
    print(f"   Memory: {info.free_memory} bytes free")
    print()
    
    # Show current relay states
    print("📋 Current Relay States:")
    for i, relay in enumerate(info.relays):
        state = "ON" if relay.state else "OFF"
        print(f"   Relay {i+1} ({relay.name}): {state}")
    print()
    
    try:
        # === SEQUENCE 1: Turn ON relays 1-4 in order ===
        print("🔥 SEQUENCE 1: Turning ON relays 1→2→3→4")
        print("-" * 40)
        
        for i in range(4):
            relay_name = info.relays[i].name
            print(f"   🔌 Relay {i+1} ({relay_name}): ON")
            
            success = controller.set_switch(i, True)
            if success:
                print(f"      ✅ Relay {i+1} activated - you should hear a click!")
            else:
                print(f"      ❌ Failed to activate relay {i+1}")
            
            time.sleep(1.5)  # Wait between activations
        
        print("\n🎉 All relays are now ON!")
        print("⏸️  Pausing for 3 seconds...")
        time.sleep(3)
        
        # === SEQUENCE 2: Turn OFF relays 4-1 in reverse order ===
        print("\n🔥 SEQUENCE 2: Turning OFF relays 4→3→2→1")
        print("-" * 40)
        
        for i in range(3, -1, -1):  # Count down from 3 to 0
            relay_name = info.relays[i].name
            print(f"   🔌 Relay {i+1} ({relay_name}): OFF")
            
            success = controller.set_switch(i, False)
            if success:
                print(f"      ✅ Relay {i+1} deactivated - you should hear a click!")
            else:
                print(f"      ❌ Failed to deactivate relay {i+1}")
            
            time.sleep(1.5)  # Wait between deactivations
        
        print("\n🎉 All relays are now OFF!")
        
        # === SEQUENCE 3: Fun pattern - Alternating ===
        print("\n🔥 SEQUENCE 3: Alternating Pattern (1&3 ON, 2&4 OFF)")
        print("-" * 50)
        
        # Turn on relays 1 and 3 (indices 0 and 2)
        for i in [0, 2]:
            relay_name = info.relays[i].name
            print(f"   🔌 Relay {i+1} ({relay_name}): ON")
            controller.set_switch(i, True)
            time.sleep(0.5)
        
        time.sleep(2)
        
        # Switch pattern: turn off 1&3, turn on 2&4
        print("\n   🔄 Switching pattern (2&4 ON, 1&3 OFF)")
        
        # Turn off relays 1 and 3
        for i in [0, 2]:
            controller.set_switch(i, False)
            time.sleep(0.2)
        
        # Turn on relays 2 and 4 (indices 1 and 3)
        for i in [1, 3]:
            relay_name = info.relays[i].name
            print(f"   🔌 Relay {i+1} ({relay_name}): ON")
            controller.set_switch(i, True)
            time.sleep(0.5)
        
        time.sleep(2)
        
        # Turn off all
        print("\n   🔌 Turning off all relays...")
        for i in range(4):
            controller.set_switch(i, False)
            time.sleep(0.3)
        
        # === SEQUENCE 4: Wave pattern ===
        print("\n🔥 SEQUENCE 4: Wave Pattern (1→2→3→4→3→2→1)")
        print("-" * 45)
        
        # Forward wave
        for i in range(4):
            relay_name = info.relays[i].name
            print(f"   🌊 Wave: Relay {i+1} ({relay_name})")
            controller.set_switch(i, True)
            time.sleep(0.6)
            controller.set_switch(i, False)
            time.sleep(0.3)
        
        # Reverse wave
        for i in range(2, -1, -1):  # 3, 2, 1 (skip 4 since we just did it)
            relay_name = info.relays[i].name
            print(f"   🌊 Wave: Relay {i+1} ({relay_name})")
            controller.set_switch(i, True)
            time.sleep(0.6)
            controller.set_switch(i, False)
            time.sleep(0.3)
        
        print("\n✨ Sequence demo complete!")
        print("\n📊 Final Status Check:")
        
        # Get final status
        final_info = controller.get_device_info()
        for i, relay in enumerate(final_info.relays):
            state = "ON" if relay.state else "OFF"
            print(f"   Relay {i+1} ({relay.name}): {state}")
        
        print(f"\n💾 Arduino Memory: {final_info.free_memory} bytes free")
        print(f"⏱️  Uptime: {final_info.uptime/1000:.1f} seconds")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted - turning off all relays...")
        for i in range(4):
            controller.set_switch(i, False)
            time.sleep(0.1)
        print("✅ All relays turned off safely")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        print("🛑 Turning off all relays for safety...")
        for i in range(4):
            try:
                controller.set_switch(i, False)
            except:
                pass
    
    finally:
        # Disconnect
        controller.disconnect()
        print("\n🔌 Disconnected from Arduino")
        print("\n🎯 Demo complete - all relays should be OFF and safe!")

if __name__ == "__main__":
    print("🎮 Starting Relay Sequence Demo...")
    print("   Make sure you can hear the relay clicks!")
    print("   Press Ctrl+C to stop at any time")
    print()
    
    # Add a countdown for dramatic effect
    for i in range(3, 0, -1):
        print(f"   Starting in {i}...")
        time.sleep(1)
    
    print("   GO! 🚀")
    print()
    
    relay_sequence_demo()