#!/usr/bin/env python3
"""
Simple Switch Controller for ObsyBox
Interactive CLI to control your relays
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from obsyswitch_serial_driver import ObsySwitchSerialController

def main():
    print("🔌 ObsyBox Switch Controller")
    print("=" * 40)
    
    controller = ObsySwitchSerialController()
    
    # Connect
    print("Connecting to Arduino...")
    if not controller.connect():
        print("❌ Failed to connect!")
        print("Check:")
        print("  - Arduino connected via USB")
        print("  - Correct sketch uploaded")
        return
    
    device_name = "Arduino Relay Controller"
    if controller.device_status:
        device_name = controller.device_status.device_name
    print(f"✅ Connected to {device_name}")
    print()
    
    while True:
        # Show current status
        print("\n📊 Current Status:")
        print("-" * 40)
        for i in range(controller.get_max_switch() + 1):
            name = controller.get_switch_name(i)
            state = controller.get_switch(i)
            icon = "🟢" if state else "⚫"
            print(f"  {icon} Switch {i}: {name:12} {'ON' if state else 'OFF'}")
        
        print("\n" + "=" * 40)
        print("Commands:")
        print("  on <0-3>  - Turn switch ON")
        print("  off <0-3> - Turn switch OFF")
        print("  toggle <0-3> - Toggle switch")
        print("  all on   - Turn all ON")
        print("  all off  - Turn all OFF")
        print("  status   - Show status")
        print("  quit     - Exit")
        print("=" * 40)
        
        cmd = input("\n> ").strip().lower()
        
        if cmd == "quit" or cmd == "q" or cmd == "exit":
            break
        
        elif cmd == "status":
            continue  # Just loop to show status
        
        elif cmd == "all on":
            for i in range(controller.get_max_switch() + 1):
                controller.set_switch(i, True)
            print("✅ All switches ON")
        
        elif cmd == "all off":
            controller.emergency_stop()
            print("✅ All switches OFF")
        
        elif cmd.startswith("on "):
            try:
                switch_id = int(cmd.split()[1])
                controller.set_switch(switch_id, True)
                name = controller.get_switch_name(switch_id)
                print(f"✅ {name} turned ON")
            except (ValueError, IndexError):
                print("❌ Usage: on <0-3>")
        
        elif cmd.startswith("off "):
            try:
                switch_id = int(cmd.split()[1])
                controller.set_switch(switch_id, False)
                name = controller.get_switch_name(switch_id)
                print(f"✅ {name} turned OFF")
            except (ValueError, IndexError):
                print("❌ Usage: off <0-3>")
        
        elif cmd.startswith("toggle "):
            try:
                switch_id = int(cmd.split()[1])
                controller.toggle_switch(switch_id)
                name = controller.get_switch_name(switch_id)
                new_state = controller.get_switch(switch_id)
                print(f"✅ {name} toggled to {'ON' if new_state else 'OFF'}")
            except (ValueError, IndexError):
                print("❌ Usage: toggle <0-3>")
        
        else:
            print("❌ Unknown command")
    
    controller.disconnect()
    print("\n👋 Disconnected. Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
