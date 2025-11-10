"""
ASCOM Switch Driver Interface for ObsyBox Relay Controller - Ethernet Version

Updated for wired Arduino Uno + Ethernet Shield deployment
IP: 192.168.1.77
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
    connection_type: str
    free_memory: int
    max_switch: int
    switches: List[SwitchInfo]

class ObsySwitchController:
    """
    Controller for ObsyBox Relay Switch Module - Ethernet Version
    
    Provides ASCOM-compatible interface to Arduino Uno + Ethernet Shield relay controller
    """
    
    def __init__(self, ip_address: str = "192.168.1.77", timeout: int = 5):
        """
        Initialize the switch controller for Ethernet version
        
        Args:
            ip_address: IP address of the Arduino Ethernet relay controller
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
        
        logger.info(f"Initialized ObsySwitchController (Ethernet) for {ip_address}")
    
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
                logger.info(f"Connected to {self.device_status.device_name} via Ethernet")
                logger.info(f"Connection type: {self.device_status.connection_type}")
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
    
    def get_connection_info(self) -> Dict[str, str]:
        """
        Get connection type and reliability info
        
        Returns:
            Dictionary with connection details
        """
        self._ensure_fresh_status()
        
        if self.device_status:
            return {
                "type": self.device_status.connection_type,
                "ip": self.device_status.ip,
                "reliability": "High - Wired Ethernet",
                "update_method": "USB Serial (always accessible)",
                "advantages": "No WiFi dependency, strong GPIO drive"
            }
        return {"type": "unknown"}
    
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
                    connection_type=status_response.get("connection_type", "ethernet") if status_response else "ethernet",
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


# Test function for Ethernet version
def test_ethernet_relay_controller():
    """Test the Ethernet relay controller functionality"""
    print("Testing ObsyBox Relay Controller - Ethernet Version...")
    
    controller = ObsySwitchController("192.168.1.77")  # Ethernet IP
    
    # Test connection
    if not controller.connect():
        print("Failed to connect to Ethernet relay controller")
        print("Check:")
        print("- Arduino Uno + Ethernet Shield powered on")
        print("- Ethernet cable connected")
        print("- IP address correct (192.168.1.77)")
        print("- Device accessible via ping")
        return False
    
    # Show connection info
    conn_info = controller.get_connection_info()
    print(f"\n✓ Connected via: {conn_info['type']}")
    print(f"✓ Reliability: {conn_info['reliability']}")
    print(f"✓ Update method: {conn_info['update_method']}")
    
    device_info = controller.get_device_info()
    if device_info:
        print(f"✓ Device: {device_info.device_name}")
        print(f"✓ Firmware: {device_info.firmware}")
        print(f"✓ IP: {device_info.ip}")
        print(f"✓ Free RAM: {device_info.free_memory} bytes")
    
    # Test switch control
    print(f"\n✓ Available switches: {controller.get_max_switch() + 1}")
    for i in range(controller.get_max_switch() + 1):
        switch_name = controller.get_switch_name(i)
        current_state = controller.get_switch(i)
        print(f"  Switch {i} ({switch_name}): {'ON' if current_state else 'OFF'}")
    
    controller.disconnect()
    print("\n🎉 Ethernet relay controller test completed!")
    return True


if __name__ == "__main__":
    test_ethernet_relay_controller()