"""
ASCOM Switch Driver for ObsyBox Relay Controller - USB Serial Version

This driver communicates with Arduino via USB Serial for direct NINA integration.
No network connection required - perfect for development and testing.

Usage:
    from obsyswitch_serial_driver import ObsySwitchSerialController
    
    # Auto-detect Arduino port
    controller = ObsySwitchSerialController()
    
    # Or specify port manually
    # controller = ObsySwitchSerialController("/dev/cu.usbserial-14120")
    
    controller.connect()
    controller.set_switch(0, True)  # Turn on relay 1 (Mount)
    controller.disconnect()
"""

import serial
import serial.tools.list_ports
import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RelayInfo:
    """Information about a single relay"""
    id: int
    name: str
    state: bool
    pin: int

@dataclass
class DeviceStatus:
    """Overall device status"""
    device_name: str
    firmware: str
    uptime: int
    free_memory: int
    relays: List[RelayInfo]

class ObsySwitchSerialController:
    """
    Serial communication controller for ObsyBox Relay Switch
    
    Communicates with Arduino via USB Serial for ASCOM/NINA integration
    """
    
    def __init__(self, port: str = None, baudrate: int = 9600, timeout: int = 5):
        """
        Initialize the serial switch controller
        
        Args:
            port: Serial port path. If None, will auto-detect Arduino
            baudrate: Serial communication speed (default 9600)
            timeout: Serial communication timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.connected = False
        self.device_status: Optional[DeviceStatus] = None
        
        # ASCOM properties
        self.max_switch = 3  # 0-based index, so 4 switches = 0-3
        
        logger.info(f"Initialized ObsySwitchSerialController (baudrate={baudrate})")
    
    def find_arduino_port(self) -> Optional[str]:
        """
        Auto-detect Arduino port
        
        Returns:
            Serial port path if found, None otherwise
        """
        logger.info("Scanning for Arduino...")
        
        ports = serial.tools.list_ports.comports()
        arduino_ports = []
        
        for port in ports:
            # Look for common Arduino identifiers
            if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'ftdi', 'cp210', 'usb']):
                arduino_ports.append(port.device)
                logger.info(f"Found potential Arduino: {port.device} - {port.description}")
        
        if len(arduino_ports) == 1:
            logger.info(f"Auto-selected Arduino port: {arduino_ports[0]}")
            return arduino_ports[0]
        elif len(arduino_ports) > 1:
            logger.warning(f"Multiple Arduino ports found: {arduino_ports}")
            logger.warning("Please specify port manually or disconnect other devices")
            return arduino_ports[0]  # Use first one
        else:
            logger.error("No Arduino ports found")
            return None
    
    def connect(self) -> bool:
        """
        Connect to the Arduino relay controller
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Auto-detect port if not specified
            if self.port is None:
                self.port = self.find_arduino_port()
                if self.port is None:
                    return False
            
            logger.info(f"Connecting to Arduino on {self.port}")
            
            # Open serial connection
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for Arduino to initialize
            time.sleep(2)
            
            # Clear any startup messages
            self._clear_serial_buffer()
            
            # Test connection with ping
            if self._send_command("PING")[0]:
                self.connected = True
                self._update_device_status()
                
                device_name = "Arduino"
                if self.device_status:
                    device_name = self.device_status.device_name
                
                logger.info(f"Connected to {device_name}")
                return True
            else:
                logger.error("Arduino not responding to ping")
                self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnect from the Arduino"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        self.serial_connection = None
        self.connected = False
        self.device_status = None
        logger.info("Disconnected from Arduino")
    
    def is_connected(self) -> bool:
        """Check if connected to Arduino"""
        return self.connected and self.serial_connection and self.serial_connection.is_open
    
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
       
        if self.device_status:
            # Find relay by converting 0-based switch_id to 1-based relay_id
            relay_id = switch_id + 1
            for relay in self.device_status.relays:
                if relay.id == relay_id:
                    return relay.name
        
        return f"Switch {switch_id + 1}"
    
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
        
        if not self.is_connected():
            raise RuntimeError("Not connected to Arduino")
        
        try:
            relay_num = switch_id + 1  # Convert to 1-based
            success, response = self._send_command(f"GET_RELAY,{relay_num}")
            
            if success and response.startswith("STATUS,"):
                # Parse JSON response
                json_str = response[7:]  # Remove "STATUS," prefix
                relay_info = json.loads(json_str)
                return relay_info.get("state", False)
            else:
                logger.error(f"Failed to get switch {switch_id} status: {response}")
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
        
        if not self.is_connected():
            raise RuntimeError("Not connected to Arduino")
        
        try:
            relay_num = switch_id + 1  # Convert to 1-based
            state_str = "ON" if state else "OFF"
           
            success, response = self._send_command(f"SET_RELAY,{relay_num},{state_str}")
            
            if success and response.startswith("OK,"):
                switch_name = self.get_switch_name(switch_id)
                logger.info(f"Switch {switch_id} ({switch_name}): {state_str}")
                
                # Update cached status
                if self.device_status:
                    relay_id = switch_id + 1  # Convert to 1-based
                    for relay in self.device_status.relays:
                        if relay.id == relay_id:
                            relay.state = state
                            break
                
                return True
            else:
                logger.error(f"Failed to set switch {switch_id}: {response}")
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
        
        if not self.is_connected():
            raise RuntimeError("Not connected to Arduino")
        
        try:
            relay_num = switch_id + 1  # Convert to 1-based
            
            success, response = self._send_command(f"SET_RELAY,{relay_num},TOGGLE")
            
            if success and response.startswith("OK,"):
                # Update cached status
                self._update_device_status()
                
                switch_name = self.get_switch_name(switch_id)
                new_state = self.get_switch(switch_id)
                state_str = "ON" if new_state else "OFF"
                logger.info(f"Switch {switch_id} ({switch_name}) toggled to: {state_str}")
                return True
            else:
                logger.error(f"Failed to toggle switch {switch_id}: {response}")
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
        if not self.is_connected():
            return {}
        
        self._update_device_status()
        
        switches = {}
        if self.device_status:
            for relay in self.device_status.relays:
                switches[relay.id - 1] = relay.state  # Convert to 0-based indexing
        
        return switches
    
    def emergency_stop(self) -> bool:
        """
        Emergency stop - turn off all switches
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        logger.warning("Emergency stop activated")
        
        try:
            success, response = self._send_command("EMERGENCY_STOP")
            
            if success and response.startswith("OK,"):
                # Update cached status
                self._update_device_status()
                logger.info("All relays turned off")
                return True
            else:
                logger.error(f"Emergency stop failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error during emergency stop: {str(e)}")
            return False
    
    def get_device_info(self) -> Optional[DeviceStatus]:
        """Get complete device information"""
        if not self.is_connected():
            return None
        
        self._update_device_status()
        return self.device_status
    
    def ping(self) -> bool:
        """
        Ping the Arduino to check if it's responding
        
        Returns:
            True if Arduino responds, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            success, response = self._send_command("PING")
            return success and response == "OK,PONG"
        except:
            return False
    
    # Private methods
    
    def _validate_switch_id(self, switch_id: int) -> bool:
        """Validate that switch_id is within valid range"""
        return 0 <= switch_id <= self.max_switch
    
    def _clear_serial_buffer(self):
        """Clear any data in the serial input buffer"""
        if self.serial_connection:
            self.serial_connection.reset_input_buffer()
            # Read and discard any startup messages
            time.sleep(0.5)
            while self.serial_connection.in_waiting > 0:
                line = self.serial_connection.readline().decode('utf-8', errors='ignore')
                if line.strip().startswith('#'):
                    logger.debug(f"Startup message: {line.strip()}")
    
    def _send_command(self, command: str) -> Tuple[bool, str]:
        """
        Send a command to Arduino and get response
        
        Args:
            command: Command string to send
            
        Returns:
            Tuple of (success, response_string)
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            return False, "Not connected"
       
        try:
            # Clear input buffer
            self.serial_connection.reset_input_buffer()
            
            # Send command
            self.serial_connection.write((command + '\n').encode('utf-8'))
            self.serial_connection.flush()
            
            # Wait for response
            start_time = time.time()
            response_lines = []
            
            while time.time() - start_time < self.timeout:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    
                    if line.startswith('#'):
                        # Debug/info message, ignore
                        logger.debug(f"Arduino: {line}")
                        continue
                    elif line.startswith('OK,') or line.startswith('ERROR,') or line.startswith('STATUS,'):
                        # Valid response
                        return True, line
                    elif line:
                        response_lines.append(line)
                
                time.sleep(0.01)  # Small delay
            
            # Timeout
            return False, f"Timeout waiting for response to: {command}"
           
        except Exception as e:
            return False, f"Communication error: {str(e)}"
    
    def _update_device_status(self):
        """Update the cached device status"""
        try:
            success, response = self._send_command("GET_STATUS")
            
            if success and response.startswith("STATUS,"):
                json_str = response[7:]  # Remove "STATUS," prefix
                status_data = json.loads(json_str)
                
                relays = []
                for relay_data in status_data.get("relays", []):
                    relays.append(RelayInfo(
                        id=relay_data["id"],
                        name=relay_data["name"],
                        state=relay_data["state"],
                        pin=relay_data["pin"]
                    ))
                
                self.device_status = DeviceStatus(
                    device_name=status_data.get("device", "Unknown"),
                    firmware=status_data.get("firmware", "Unknown"),
                    uptime=status_data.get("uptime", 0),
                    free_memory=status_data.get("free_memory", 0),
                    relays=relays
                )
                
        except Exception as e:
            logger.error(f"Failed to update device status: {str(e)}")


class ASCOMSwitchSerial:
    """
    ASCOM Switch interface wrapper for ObsySwitchSerialController
    
    Provides ASCOM-compatible interface for use with astronomy software
    """
    
    def __init__(self, port: str = None):
        self.controller = ObsySwitchSerialController(port)
        self.driver_info = {
            "Name": "ObsyBox Relay Switch - Serial",
            "Description": "ASCOM Switch driver for ObsyBox relay controller via USB Serial",
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


# Example/Test function
def test_serial_relay_controller():
    """Test the serial relay controller"""
    print("Testing ObsyBox Relay Controller - USB Serial Version")
    print("=" * 60)
    
    # Create controller (auto-detect port)
    controller = ObsySwitchSerialController()
    
    try:
        # Connect
        print("Connecting to Arduino...")
        if not controller.connect():
            print(f"Failed to connect to Arduino")
            print("Check:")
            print(f" - Arduino is connected via USB")
            print(f" - Correct USB drivers installed")
            print(f" - RelayController_Serial sketch uploaded")
            print(f" - No other programs using the serial port")
            return False
        
        print(f"Connected successfully!")
        
        # Get device info
        device_info = controller.get_device_info()
        if device_info:
            print(f"Device: {device_info.device_name}")
            print(f"Firmware: {device_info.firmware}")
            print(f"Uptime: {device_info.uptime / 1000:.1f} seconds")
            print(f"Free RAM: {device_info.free_memory} bytes")
        
        # Show switch status
        print(f"\nAvailable switches: {controller.get_max_switch() + 1}")
        all_switches = controller.get_all_switches()
        for switch_id, state in all_switches.items():
            switch_name = controller.get_switch_name(switch_id)
            print(f"Switch {switch_id} ({switch_name}): {'ON' if state else 'OFF'}")
        
        # Test switch control
        print(f"\nTesting switch control...")
        
        # Test switch 0 (Mount)
        print("Testing Mount relay (Switch 0)...")
        original_state = controller.get_switch(0)
        print(f"Original state: {'ON' if original_state else 'OFF'}")
        
        # Toggle it
        print(f"Toggling...")
        controller.toggle_switch(0)
        time.sleep(1)
        
        new_state = controller.get_switch(0)
        print(f"New state: {'ON' if new_state else 'OFF'}")
        
        # Toggle back
        print(f"Toggling back...")
        controller.toggle_switch(0)
        time.sleep(1)
        
        final_state = controller.get_switch(0)
        print(f"Final state: {'ON' if final_state else 'OFF'}")
        
        if final_state == original_state:
            print(f"  Switch control test passed!")
        else:
            print(f"   Switch state mismatch")
        
        print(f"\nAll tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False
        
    finally:
        controller.disconnect()
        print("Disconnected from Arduino")


if __name__ == "__main__":
    # Run test when executed directly
    test_serial_relay_controller()