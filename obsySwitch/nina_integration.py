"""
NINA Integration Example for ObsyBox Relay Controller

This module demonstrates how to integrate the relay controller with NINA
for automated observatory equipment control.

Features:
- Pre-sequence equipment power-up
- Post-sequence equipment shutdown
- Safety interlocks
- Error handling
"""

import time
import logging
from typing import Dict, List
from obsyswitch_driver import ObsySwitchController

logger = logging.getLogger(__name__)

class NINAObservatoryController:
    """
    Observatory equipment controller for NINA integration
    
    Manages power control of observatory equipment with safety checks
    and proper sequencing for automated observations.
    """
    
    def __init__(self, relay_ip: str = "192.168.1.76"):
        self.relay_controller = ObsySwitchController(relay_ip)
        
        # Equipment mapping (switch_id: equipment_name)
        self.equipment = {
            0: "Mount",      # Telescope mount
            1: "Camera",     # Imaging camera  
            2: "Focuser",    # Auto focuser
            3: "Auxiliary"   # Auxiliary equipment
        }
        
        # Startup sequence order (switch_id)
        self.startup_sequence = [0, 2, 1, 3]  # Mount → Focuser → Camera → Aux
        
        # Shutdown sequence order (reverse of startup)
        self.shutdown_sequence = [3, 1, 2, 0]  # Aux → Camera → Focuser → Mount
        
        # Timing delays between power operations (seconds)
        self.power_on_delay = 2.0
        self.power_off_delay = 1.0
        
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to relay controller"""
        try:
            self.connected = self.relay_controller.connect()
            if self.connected:
                logger.info("Observatory controller connected successfully")
            return self.connected
        except Exception as e:
            logger.error(f"Failed to connect to observatory controller: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from relay controller"""
        try:
            self.relay_controller.disconnect()
            self.connected = False
            logger.info("Observatory controller disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    def pre_sequence_startup(self, required_equipment: List[str] = None) -> bool:
        """
        Start up equipment before beginning observation sequence
        
        Args:
            required_equipment: List of equipment names to power on.
                              If None, powers on all equipment.
        
        Returns:
            True if all equipment started successfully
        """
        if not self.connected:
            logger.error("Not connected to relay controller")
            return False
        
        logger.info("Starting pre-sequence equipment startup")
        
        # Determine which equipment to start
        if required_equipment is None:
            # Start all equipment in proper sequence
            switches_to_start = self.startup_sequence
        else:
            # Start only requested equipment
            switches_to_start = []
            for switch_id, equipment_name in self.equipment.items():
                if equipment_name in required_equipment:
                    switches_to_start.append(switch_id)
            
            # Sort by startup sequence order
            switches_to_start.sort(key=lambda x: self.startup_sequence.index(x))
        
        # Power on equipment in sequence
        success = True
        for switch_id in switches_to_start:
            equipment_name = self.equipment[switch_id]
            logger.info(f"Powering on {equipment_name}...")
            
            try:
                if self.relay_controller.set_switch(switch_id, True):
                    logger.info(f"✓ {equipment_name} powered on successfully")
                    time.sleep(self.power_on_delay)
                else:
                    logger.error(f"✗ Failed to power on {equipment_name}")
                    success = False
                    
            except Exception as e:
                logger.error(f"✗ Error powering on {equipment_name}: {e}")
                success = False
        
        if success:
            logger.info("Pre-sequence startup completed successfully")
        else:
            logger.error("Pre-sequence startup encountered errors")
            
        return success
    
    def post_sequence_shutdown(self, equipment_to_keep_on: List[str] = None) -> bool:
        """
        Shut down equipment after observation sequence
        
        Args:
            equipment_to_keep_on: List of equipment names to keep powered.
                                If None, shuts down all equipment.
        
        Returns:
            True if all equipment shut down successfully
        """
        if not self.connected:
            logger.error("Not connected to relay controller")
            return False
        
        logger.info("Starting post-sequence equipment shutdown")
        
        # Determine which equipment to shut down
        if equipment_to_keep_on is None:
            # Shut down all equipment in proper sequence
            switches_to_shutdown = self.shutdown_sequence
        else:
            # Shut down all except those to keep on
            switches_to_shutdown = []
            for switch_id, equipment_name in self.equipment.items():
                if equipment_name not in equipment_to_keep_on:
                    switches_to_shutdown.append(switch_id)
            
            # Sort by shutdown sequence order
            switches_to_shutdown.sort(key=lambda x: self.shutdown_sequence.index(x))
        
        # Power off equipment in sequence
        success = True
        for switch_id in switches_to_shutdown:
            equipment_name = self.equipment[switch_id]
            logger.info(f"Powering off {equipment_name}...")
            
            try:
                if self.relay_controller.set_switch(switch_id, False):
                    logger.info(f"✓ {equipment_name} powered off successfully")
                    time.sleep(self.power_off_delay)
                else:
                    logger.error(f"✗ Failed to power off {equipment_name}")
                    success = False
                    
            except Exception as e:
                logger.error(f"✗ Error powering off {equipment_name}: {e}")
                success = False
        
        if success:
            logger.info("Post-sequence shutdown completed successfully")
        else:
            logger.error("Post-sequence shutdown encountered errors")
            
        return success
    
    def emergency_shutdown(self) -> bool:
        """
        Emergency shutdown of all equipment
        
        Returns:
            True if emergency shutdown successful
        """
        logger.warning("EMERGENCY SHUTDOWN INITIATED")
        
        if not self.connected:
            logger.error("Not connected to relay controller for emergency shutdown")
            return False
        
        try:
            success = self.relay_controller.emergency_stop()
            if success:
                logger.info("✓ Emergency shutdown completed")
            else:
                logger.error("✗ Emergency shutdown failed")
            return success
            
        except Exception as e:
            logger.error(f"✗ Error during emergency shutdown: {e}")
            return False
    
    def get_equipment_status(self) -> Dict[str, bool]:
        """
        Get current status of all equipment
        
        Returns:
            Dictionary mapping equipment names to their power states
        """
        if not self.connected:
            return {}
        
        try:
            switch_states = self.relay_controller.get_all_switches()
            equipment_status = {}
            
            for switch_id, equipment_name in self.equipment.items():
                equipment_status[equipment_name] = switch_states.get(switch_id, False)
            
            return equipment_status
            
        except Exception as e:
            logger.error(f"Error getting equipment status: {e}")
            return {}
    
    def check_safety_conditions(self) -> tuple[bool, List[str]]:
        """
        Check safety conditions before equipment operation
        
        Returns:
            Tuple of (is_safe, list_of_issues)
        """
        issues = []
        
        # Check relay controller connectivity
        if not self.connected:
            issues.append("Relay controller not connected")
        
        # Check device responsiveness
        if self.connected and not self.relay_controller.ping():
            issues.append("Relay controller not responding")
        
        # Check WiFi signal strength
        if self.connected:
            try:
                rssi = self.relay_controller.get_signal_strength()
                if rssi < -80:  # Very weak signal
                    issues.append(f"Weak WiFi signal: {rssi} dBm")
            except:
                issues.append("Unable to check WiFi signal strength")
        
        # Add more safety checks as needed:
        # - Weather conditions
        # - Sun position
        # - Dome/roof position
        # - etc.
        
        is_safe = len(issues) == 0
        return is_safe, issues


# NINA Integration Functions

def nina_pre_sequence_hook(equipment_list: List[str] = None) -> bool:
    """
    NINA pre-sequence hook function
    Call this at the start of your NINA sequence
    """
    controller = NINAObservatoryController()
    
    try:
        if not controller.connect():
            logger.error("Failed to connect to observatory controller")
            return False
        
        # Check safety conditions
        is_safe, issues = controller.check_safety_conditions()
        if not is_safe:
            logger.error(f"Safety check failed: {issues}")
            return False
        
        # Start up equipment
        return controller.pre_sequence_startup(equipment_list)
        
    except Exception as e:
        logger.error(f"Pre-sequence hook failed: {e}")
        return False
    finally:
        controller.disconnect()

def nina_post_sequence_hook(keep_on: List[str] = None) -> bool:
    """
    NINA post-sequence hook function
    Call this at the end of your NINA sequence
    """
    controller = NINAObservatoryController()
    
    try:
        if not controller.connect():
            logger.error("Failed to connect to observatory controller")
            return False
        
        # Shut down equipment
        return controller.post_sequence_shutdown(keep_on)
        
    except Exception as e:
        logger.error(f"Post-sequence hook failed: {e}")
        return False
    finally:
        controller.disconnect()

def nina_emergency_stop() -> bool:
    """
    NINA emergency stop function
    Call this in error handling or emergency situations
    """
    controller = NINAObservatoryController()
    
    try:
        if not controller.connect():
            logger.error("Failed to connect for emergency stop")
            return False
        
        return controller.emergency_shutdown()
        
    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        return False
    finally:
        controller.disconnect()


# Example Usage

def example_nina_sequence():
    """
    Example of how to integrate with a NINA sequence
    """
    logger.info("Starting NINA sequence with ObsyBox relay control")
    
    try:
        # Pre-sequence startup
        logger.info("Phase 1: Equipment startup")
        if not nina_pre_sequence_hook(["Mount", "Camera", "Focuser"]):
            logger.error("Equipment startup failed")
            return False
        
        # Simulate NINA sequence activities
        logger.info("Phase 2: Imaging sequence")
        time.sleep(2)  # Placeholder for actual NINA sequence
        
        # Post-sequence shutdown
        logger.info("Phase 3: Equipment shutdown")
        if not nina_post_sequence_hook(["Mount"]):  # Keep mount on for next sequence
            logger.error("Equipment shutdown failed")
            return False
        
        logger.info("NINA sequence completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"NINA sequence failed: {e}")
        # Emergency shutdown on error
        nina_emergency_stop()
        return False


if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example sequence
    example_nina_sequence()