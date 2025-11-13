#!/usr/bin/env python3
"""
NINA Serial Integration Script for ObsyBox Relay Controller

This script provides startup/shutdown sequences for NINA integration.
Can be called directly from NINA as an external script or used interactively.

Usage:
    python nina_serial_integration.py startup    # Power on equipment sequence
    python nina_serial_integration.py shutdown   # Power off all equipment
    python nina_serial_integration.py status     # Show current status
    python nina_serial_integration.py toggle 0   # Toggle specific switch
    python nina_serial_integration.py            # Interactive mode

Integration with NINA:
    Add "External Script" instruction with:
    Program: python
    Arguments: /full/path/to/nina_serial_integration.py startup
"""

import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from obsyswitch_serial_driver import ObsySwitchSerialController
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure obsyswitch_serial_driver.py is in the same directory")
    print("And that pyserial is installed: pip install pyserial")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('obsybox_relay_control.log')
    ]
)
logger = logging.getLogger(__name__)

# Equipment configuration - Updated based on test results
EQUIPMENT_CONFIG = {
    0: {
        'name': 'Mount',
        'description': 'Telescope mount power',
        'startup_delay': 3,  # seconds to wait after activation
        'priority': 1        # startup order (lower = first)
    },
    1: {
        'name': 'Camera',
        'description': 'Main imaging camera',
        'startup_delay': 2,
        'priority': 3
    },
    2: {
        'name': 'Focuser',
        'description': 'Electronic focuser',
        'startup_delay': 1,
        'priority': 2
    },
    # Note: Relay 4 (Switch 3) not working - commented out for now
    # 3: {
    #     'name': 'Aux',
    #     'description': 'Auxiliary equipment',
    #     'startup_delay': 1,
    #     'priority': 4
    # }
}

def log_action(action, success=True, details=""):
    """Log actions with timestamp for NINA log correlation"""
    timestamp = datetime.now().isoformat()
    status = " SUCCESS" if success else " FAILED"
    message = f"{status} {action}"
   
    if details:
        message += f" - {details}"
   
    logger.info(message)
    print(f"[{timestamp}] {message}")

def get_controller():
    """Get a connected controller instance"""
    try:
        controller = ObsySwitchSerialController()
        
        if not controller.connect():
            raise RuntimeError("Failed to connect to Arduino")
        
        return controller
        
    except Exception as e:
        log_action(f"Controller connection", False, str(e))
        return None

def startup_sequence(conditional_dew_heater=True):
    """
    Power on equipment in proper startup order
    
    Args:
        conditional_dew_heater: Only activate dew heater if conditions require it
    """
    print(f"Starting ObsyBox Observatory Equipment")
    print("=" * 50)
    
    controller = get_controller()
    if not controller:
        return False
    
    try:
        # Get current status
        all_switches = controller.get_all_switches()
        log_action("Startup sequence initiated")
        
        # Sort equipment by startup priority
        startup_order = sorted(
            EQUIPMENT_CONFIG.items(),
            key=lambda x: x[1]['priority']
        )
        
        success_count = 0
        
        for switch_id, config in startup_order:
            name = config['name']
            delay = config['startup_delay']
            
            # Special handling for dew heater
            if switch_id == 2 and conditional_dew_heater:
                if not check_dew_heater_conditions():
                    log_action(f"Skipping {name} (conditions not met)")
                    continue
            
            # Check if already on
            if all_switches.get(switch_id, False):
                log_action(f"{name} already powered on")
                success_count += 1
                continue
            
            # Power on the equipment
            print(f"Powering on {name}...")
            
            if controller.set_switch(switch_id, True):
                log_action(f"Powered on {name}")
                success_count += 1
                
                if delay > 0:
                    print(f"    Waiting {delay} seconds for {name} to initialize...")
                    time.sleep(delay)
            else:
                log_action(f"Failed to power on {name}", False)
        
        # Final status check
        time.sleep(1)
        final_status = controller.get_all_switches()
        active_count = sum(1 for state in final_status.values() if state)
        
        print(f"\nStartup Summary:")
        print(f"   {success_count} devices powered on successfully")
        print(f"   {active_count} total devices active")
        
        if success_count > 0:
            log_action(f"Observatory startup complete ({success_count} devices)")
            print(f"Observatory ready for observations!")
            return True
        else:
            log_action("Observatory startup failed", False)
            return False
            
    except Exception as e:
        log_action(f"Startup sequence error", False, str(e))
        return False
        
    finally:
        controller.disconnect()

def shutdown_sequence():
    """
    Safely power down all equipment
    """
    print(f"Shutting Down ObsyBox Observatory Equipment")
    print("=" * 50)
    
    controller = get_controller()
    if not controller:
        return False
    
    try:
        # Get current status
        all_switches = controller.get_all_switches()
        active_devices = [
            f"Switch {id} ({EQUIPMENT_CONFIG[id]['name']})"
            for id, state in all_switches.items()
            if state and id in EQUIPMENT_CONFIG
        ]
        
        if not active_devices:
            log_action("All equipment already powered off")
            print(f"All equipment already powered off")
            return True
        
        print(f"Active devices: {', '.join([name.split('(')[1].rstrip(')') for name in active_devices])}")
        
        # Emergency stop - turn everything off
        print(f"Emergency stop - powering off all equipment...")
        
        if controller.emergency_stop():
            log_action("Emergency stop executed - all equipment powered off")
            print(f"All equipment safely powered off")
            
            # Wait a moment for relays to settle
            time.sleep(2)
            
            # Verify shutdown
            final_status = controller.get_all_switches()
            still_active = sum(1 for state in final_status.values() if state)
            
            if still_active == 0:
                print(f"Observatory shutdown complete")
                return True
            else:
                log_action(f"Shutdown verification failed - {still_active} devices still active", False)
                return False
        else:
            log_action("Emergency stop failed", False)
            return False
            
    except Exception as e:
        log_action(f"Shutdown sequence error", False, str(e))
        return False
        
    finally:
        controller.disconnect()

def show_status():
    """Display current equipment status"""
    print(f"ObsyBox Equipment Status")
    print("=" * 40)
    
    controller = get_controller()
    if not controller:
        return False
    
    try:
        # Get device info
        device_info = controller.get_device_info()
        all_switches = controller.get_all_switches()
        
        if device_info:
            print(f"Device: {device_info.device_name}")
            print(f"Firmware: {device_info.firmware}")
            print(f"Uptime: {device_info.uptime / 1000:.1f} seconds")
            print(f"Free RAM: {device_info.free_memory} bytes")
            print()
        
        print(f"Equipment Status:")
        active_count = 0
        
        for switch_id in sorted(EQUIPMENT_CONFIG.keys()):
            config = EQUIPMENT_CONFIG[switch_id]
            state = all_switches.get(switch_id, False)
            status_icon = "" if state else ""
            status_text = "ON " if state else "OFF"
           
            print(f"  {status_icon} Switch {switch_id} ({config['name']}): {status_text}")
            
            if state:
                active_count += 1
        
        print(f"\nSummary: {active_count}/{len(EQUIPMENT_CONFIG)} devices powered on")
        
        if active_count == 0:
            print(f"Observatory in standby mode")
        elif active_count == len(EQUIPMENT_CONFIG):
            print(f"Observatory fully operational")
        else:
            print(f"Partial power state - check equipment")
        
        return True
        
    except Exception as e:
        log_action(f"Status check error", False, str(e))
        return False
        
    finally:
        controller.disconnect()

def toggle_switch(switch_id):
    """Toggle a specific switch"""
    if switch_id not in EQUIPMENT_CONFIG:
        print(f"Invalid switch ID: {switch_id}")
        print(f"Valid switches: {list(EQUIPMENT_CONFIG.keys())}")
        return False
    
    config = EQUIPMENT_CONFIG[switch_id]
    print(f"Toggling {config['name']} (Switch {switch_id})")
    
    controller = get_controller()
    if not controller:
        return False
    
    try:
        old_state = controller.get_switch(switch_id)
        
        if controller.toggle_switch(switch_id):
            new_state = controller.get_switch(switch_id)
            action = "ON" if new_state else "OFF"
            log_action(f"Toggled {config['name']} to {action}")
            print(f"{config['name']} is now {action}")
            return True
        else:
            log_action(f"Failed to toggle {config['name']}", False)
            return False
            
    except Exception as e:
        log_action(f"Toggle error for {config['name']}", False, str(e))
        return False
        
    finally:
        controller.disconnect()

def check_dew_heater_conditions():
    """
    Check if dew heater should be activated
    
    This is a placeholder - integrate with your weather monitoring
    """
    try:
        # Example: Check time of night (dew forms after midnight)
        current_hour = datetime.now().hour
        if 0 <= current_hour <= 6:
            return True
        
        # Example: Could integrate with weather station
        # import requests
        # weather = requests.get("http://192.168.1.183/humidity").json()
        # humidity = weather.get("humidity", 0)
        # return humidity > 80.0
        
        # Example: Could check MQTT weather safety
        # import paho.mqtt.client as mqtt
        # Check obsybox/weathersafety topic for humidity/dew point
        
        # For now, return True (always activate)
        return True
        
    except Exception as e:
        logger.warning(f"Dew heater condition check failed: {e}")
        return False  # Default to not activating on error

def interactive_mode():
    """Interactive control mode"""
    print(f"ObsyBox Interactive Control Mode")
    print("=" * 40)
    
    while True:
        print("\nCommands:")
        print(f" 1) Show status")
        print(f" 2) Startup sequence")
        print(f" 3) Shutdown sequence")
        print(f" 4) Toggle switch")
        print(f" 5) Emergency stop")
        print(f" q) Quit")
        
        try:
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'q':
                print(f"Goodbye!")
                break
            elif choice == '1':
                show_status()
            elif choice == '2':
                startup_sequence()
            elif choice == '3':
                shutdown_sequence()
            elif choice == '4':
                print("\nAvailable switches:")
                for switch_id, config in EQUIPMENT_CONFIG.items():
                    print(f" {switch_id}) {config['name']}")
                
                try:
                    switch_id = int(input("Enter switch ID: "))
                    toggle_switch(switch_id)
                except ValueError:
                    print(f"Invalid switch ID")
            elif choice == '5':
                if input("  Confirm emergency stop (y/N): ").lower() == 'y':
                    shutdown_sequence()
            else:
                print(f"Invalid choice")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='ObsyBox Relay Controller - NINA Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python nina_serial_integration.py startup     # Power on sequence
    python nina_serial_integration.py shutdown    # Power off all
    python nina_serial_integration.py status      # Show current status
    python nina_serial_integration.py toggle 0    # Toggle mount
    python nina_serial_integration.py             # Interactive mode

NINA Integration:
    Add as External Script with arguments: startup or shutdown
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=['startup', 'shutdown', 'status', 'toggle'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'switch_id',
        nargs='?',
        type=int,
        help='Switch ID for toggle command (0-3)'
    )
    
    parser.add_argument(
        '--no-dew-heater',
        action='store_true',
        help='Skip dew heater activation during startup'
    )
    
    args = parser.parse_args()
    
    # If no command provided, enter interactive mode
    if args.command is None:
        interactive_mode()
        return
    
    # Execute the requested command
    success = False
    
    if args.command == 'startup':
        success = startup_sequence(not args.no_dew_heater)
    elif args.command == 'shutdown':
        success = shutdown_sequence()
    elif args.command == 'status':
        success = show_status()
    elif args.command == 'toggle':
        if args.switch_id is None:
            print(f"Toggle command requires switch ID")
            print("Usage: python nina_serial_integration.py toggle <switch_id>")
            print(f"Valid switch IDs: {list(EQUIPMENT_CONFIG.keys())}")
        else:
            success = toggle_switch(args.switch_id)
    
    # Exit with appropriate code for NINA
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()