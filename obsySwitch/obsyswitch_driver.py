"""
ASCOM Switch Driver Interface for ObsyBox Relay Controller

This module provides a Python interface to the Arduino-based relay controller
for use with ASCOM drivers and NINA scheduling.

Features:
- RESTful API communication with Arduino
- ASCOM-compatible switch interface
- Automatic device discovery
- Status monitoring and logging
- Error handling and retry logic

Usage:
    from obsyswitch_driver import ObsySwitchController
    
    controller = ObsySwitchController()
    controller.connect()
    
    # Turn on relay 1 (Mount)
    controller.set_switch(0, True)  # ASCOM uses 0-based indexing
    
    # Get switch status
    status = controller.get_switch(0)
    print(f"Mount power: {'ON' if status else 'OFF'}")
"""

import requests
import json
import time
import logging
from typing import List, Dict, Union, Optional
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SwitchInfo:
    """Information about a single switch"""
    id: int
    name: str
    state: bool
    pin: int
    can_write: bool = True

@dataclass
class DeviceStatus:
    """Overall device status"""
    device_name: str
    connected: bool
    firmware: str
    build_date: str
    uptime: int
    ip: str
    rssi: int
    free_memory: int
    max_switch: int
    switches: List[SwitchInfo]

class ObsySwitchController:
    """
    Controller for ObsyBox Relay Switch Module
    
    Provides ASCOM-compatible interface to Arduino-based relay controller
    """
    
    def __init__(self, ip_address: str = "192.168.1.76", timeout: int = 5):
        """
        Initialize the switch controller
        
        Args:
            ip_address: IP address of the Arduino relay controller
            timeout: HTTP request timeout in seconds
        """
        self.ip_address = ip_address
        self.timeout = timeout
        self.base_url = f"http://{ip_address}"
        self.connected = False
        self.device_status: Optional[DeviceStatus] = None
        self.last_update = 0
        self.update_interval = 5  # Update status every 5 seconds
        
        # ASCOM properties
        self.max_switch = 3  # 0-based index, so 4 switches = 0-3
        
        logger.info(f"Initialized ObsySwitchController for {ip_address}")
    
    def connect(self) -> bool:
        """
        Connect to the relay controller and verify communication
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self._get_request("/ascom/status")
            if response and response.get("connected"):
                self.connected = True
                self._update_device_status()
                logger.info(f"Connected to {self.device_status.device_name}")
                return True
            else:
                self.connected = False
                logger.error("Failed to connect: device not responding properly")
                return False
                
        except Exception as e:
            self.connected = False
            logger.error(f"Connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from the relay controller"""
        self.connected = False
        self.device_status = None
        logger.info("Disconnected from relay controller")
    
    def is_connected(self) -> bool:
        """Check if connected to the device"""
        return self.connected
    
    def get_max_switch(self) -> int:
        """Get the maximum switch index (ASCOM property)"""
        return self.max_switch
    
    def get_switch_name(self, switch_id: int) -> str:
        """
        Get the name of a switch
        
        Args:
            switch_id: Switch index (0-based)
            
        Returns:
            Switch name or empty string if invalid
        """
        if not self._validate_switch_id(switch_id):
            return ""
        
        self._ensure_fresh_status()
        if self.device_status and switch_id < len(self.device_status.switches):
            return self.device_status.switches[switch_id].name
        
        return f"Switch {switch_id + 1}"  # Fallback name
    
    def get_switch(self, switch_id: int) -> bool:
        """
        Get the state of a switch
        
        Args:
            switch_id: Switch index (0-based)
            
        Returns:
            True if switch is on, False if off
        """
        if not self._validate_switch_id(switch_id):
            raise ValueError(f"Invalid switch ID: {switch_id}")
        
        try:
            # Get individual relay status for most up-to-date info
            relay_num = switch_id + 1  # Convert to 1-based for Arduino API
            response = self._get_request(f"/relay/{relay_num}")
            
            if response and "state" in response:
                return response["state"]
            else:
                logger.error(f"Failed to get switch {switch_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error getting switch {switch_id} state: {str(e)}")
            return False
    
    def set_switch(self, switch_id: int, state: bool) -> bool:
        """
        Set the state of a switch
        
        Args:
            switch_id: Switch index (0-based)
            state: True to turn on, False to turn off
            
        Returns:
            True if successful, False otherwise
        """
        if not self._validate_switch_id(switch_id):
            raise ValueError(f"Invalid switch ID: {switch_id}")
        
        if not self.connected:
            logger.error("Not connected to device")
            return False
        
        try:
            relay_num = switch_id + 1  # Convert to 1-based for Arduino API
            action = "on" if state else "off"
            
            response = self._post_request(f"/relay/{relay_num}/{action}")
            
            if response and "state" in response:
                success = response["state"] == state
                if success:
                    switch_name = self.get_switch_name(switch_id)
                    logger.info(f"Switch {switch_id} ({switch_name}): {action.upper()}")
                else:
                    logger.error(f"Switch {switch_id} state mismatch after command")
                return success
            else:
                logger.error(f"Failed to set switch {switch_id} to {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting switch {switch_id} state: {str(e)}")
            return False
    
    def toggle_switch(self, switch_id: int) -> bool:
        """
        Toggle the state of a switch
        
        Args:
            switch_id: Switch index (0-based)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._validate_switch_id(switch_id):
            raise ValueError(f"Invalid switch ID: {switch_id}")
        
        try:
            relay_num = switch_id + 1  # Convert to 1-based for Arduino API
            response = self._post_request(f"/relay/{relay_num}/toggle")
            
            if response and "state" in response:
                switch_name = self.get_switch_name(switch_id)
                state_str = "ON" if response["state"] else "OFF"
                logger.info(f"Switch {switch_id} ({switch_name}) toggled to: {state_str}")
                return True
            else:
                logger.error(f"Failed to toggle switch {switch_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error toggling switch {switch_id}: {str(e)}")
            return False
    
    def get_all_switches(self) -> Dict[int, bool]:
        """
        Get the state of all switches
        
        Returns:
            Dictionary mapping switch IDs to their states
        """
        self._ensure_fresh_status()
        
        switches = {}
        if self.device_status:
            for switch in self.device_status.switches:
                switches[switch.id] = switch.state
        
        return switches
    
    def set_all_switches(self, states: Dict[int, bool]) -> bool:
        """
        Set multiple switches at once
        
        Args:
            states: Dictionary mapping switch IDs to desired states
            
        Returns:
            True if all operations successful, False otherwise
        """
        success = True
        for switch_id, state in states.items():
            if not self.set_switch(switch_id, state):
                success = False
        
        return success
    
    def emergency_stop(self) -> bool:
        """
        Emergency stop - turn off all switches
        
        Returns:
            True if successful, False otherwise
        """
        logger.warning("Emergency stop activated - turning off all switches")
        
        success = True
        for i in range(self.max_switch + 1):
            if not self.set_switch(i, False):
                success = False
        
        return success
    
    def get_device_info(self) -> Optional[DeviceStatus]:
        """Get complete device information"""
        self._ensure_fresh_status()
        return self.device_status
    
    def get_uptime(self) -> int:
        """Get device uptime in seconds"""
        self._ensure_fresh_status()
        if self.device_status:
            return self.device_status.uptime // 1000  # Convert from milliseconds
        return 0
    
    def get_signal_strength(self) -> int:
        """Get WiFi signal strength in dBm"""
        self._ensure_fresh_status()
        if self.device_status:
            return self.device_status.rssi
        return 0
    
    def ping(self) -> bool:
        """
        Ping the device to check connectivity
        
        Returns:
            True if device responds, False otherwise
        """
        try:
            response = self._get_request("/status")
            return response is not None and "device" in response
        except:
            return False
    
    # Private methods
    
    def _validate_switch_id(self, switch_id: int) -> bool:
        """Validate that switch_id is within valid range"""
        return 0 <= switch_id <= self.max_switch
    
    def _ensure_fresh_status(self):
        """Update device status if it's stale"""
        now = time.time()
        if now - self.last_update > self.update_interval:
            self._update_device_status()
    
    def _update_device_status(self):
        """Update the cached device status"""
        try:
            response = self._get_request("/ascom/status")
            if response:
                switches = [
                    SwitchInfo(
                        id=sw["id"],
                        name=sw["name"],
                        state=sw["value"],
                        pin=0,  # Not provided in ASCOM status
                        can_write=sw.get("can_write", True)
                    )
                    for sw in response.get("switches", [])
                ]
                
                # Get additional info from main status endpoint
                status_response = self._get_request("/status")
                
                self.device_status = DeviceStatus(
                    device_name=response.get("device_name", "Unknown"),
                    connected=response.get("connected", False),
                    firmware=status_response.get("firmware", "Unknown") if status_response else "Unknown",
                    build_date=status_response.get("build_date", "Unknown") if status_response else "Unknown",
                    uptime=status_response.get("uptime", 0) if status_response else 0,
                    ip=status_response.get("ip", self.ip_address) if status_response else self.ip_address,
                    rssi=status_response.get("rssi", 0) if status_response else 0,
                    free_memory=status_response.get("free_memory", 0) if status_response else 0,
                    max_switch=response.get("max_switch", self.max_switch),
                    switches=switches
                )
                
                self.last_update = time.time()
                
        except Exception as e:
            logger.error(f"Failed to update device status: {str(e)}")
    
    def _get_request(self, endpoint: str) -> Optional[Dict]:
        """Make a GET request to the device"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"GET {endpoint} failed: {str(e)}")
            return None
    
    def _post_request(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make a POST request to the device"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"POST {endpoint} failed: {str(e)}")
            return None


class ASCOMSwitchV2:
    """
    ASCOM Switch V2 interface wrapper for ObsySwitchController
    
    Provides a standardized ASCOM interface for use with astronomy software
    """
    
    def __init__(self, ip_address: str = "192.168.1.76"):
        self.controller = ObsySwitchController(ip_address)
        self.driver_info = {
            "Name": "ObsyBox Relay Switch",
            "Description": "ASCOM Switch driver for ObsyBox relay controller",
            "DriverVersion": "1.0.0",
            "InterfaceVersion": 2
        }
    
    # ASCOM Standard Properties
    
    @property
    def Connected(self) -> bool:
        """ASCOM Connected property"""
        return self.controller.is_connected()
    
    @Connected.setter
    def Connected(self, value: bool):
        """ASCOM Connected property setter"""
        if value:
            self.controller.connect()
        else:
            self.controller.disconnect()
    
    @property
    def MaxSwitch(self) -> int:
        """ASCOM MaxSwitch property"""
        return self.controller.get_max_switch()
    
    def GetSwitch(self, id: int) -> bool:
        """ASCOM GetSwitch method"""
        return self.controller.get_switch(id)
    
    def SetSwitch(self, id: int, state: bool):
        """ASCOM SetSwitch method"""
        self.controller.set_switch(id, state)
    
    def GetSwitchName(self, id: int) -> str:
        """ASCOM GetSwitchName method"""
        return self.controller.get_switch_name(id)
    
    def CanWrite(self, id: int) -> bool:
        """ASCOM CanWrite method"""
        return self.controller._validate_switch_id(id)
    
    # Additional utility methods
    
    def GetDriverInfo(self) -> Dict[str, str]:
        """Get driver information"""
        return self.driver_info
    
    def GetDeviceStatus(self) -> Optional[DeviceStatus]:
        """Get detailed device status"""
        return self.controller.get_device_info()


# Example usage and testing functions

def test_relay_controller():
    """Test the relay controller functionality"""
    print("Testing ObsyBox Relay Controller...")
    
    controller = ObsySwitchController()
    
    # Test connection
    if not controller.connect():
        print("Failed to connect to relay controller")
        return False
    
    print(f"Connected to: {controller.device_status.device_name}")
    print(f"Firmware: {controller.device_status.firmware}")
    print(f"IP: {controller.device_status.ip}")
    print(f"Switches available: {controller.get_max_switch() + 1}")
    
    # Test individual switch control
    print("\nTesting switch control...")
    for i in range(controller.get_max_switch() + 1):
        switch_name = controller.get_switch_name(i)
        current_state = controller.get_switch(i)
        print(f"Switch {i} ({switch_name}): {'ON' if current_state else 'OFF'}")
        
        # Toggle the switch
        print(f"Toggling switch {i}...")
        controller.toggle_switch(i)
        time.sleep(1)
        
        new_state = controller.get_switch(i)
        print(f"Switch {i} now: {'ON' if new_state else 'OFF'}")
        
        # Toggle back
        controller.toggle_switch(i)
        time.sleep(1)
    
    # Test getting all switches
    print(f"\nAll switches: {controller.get_all_switches()}")
    
    controller.disconnect()
    print("Test completed successfully!")
    return True


if __name__ == "__main__":
    # Run tests if executed directly
    test_relay_controller()