# ObsyBox Relay Controller Configuration

## Device Settings
DEVICE_IP = "192.168.1.76"
DEVICE_NAME = "ObsySwitch"
TIMEOUT = 5  # HTTP request timeout in seconds

## Relay Configuration
# Map relay numbers (1-4) to their purposes
RELAY_NAMES = {
    1: "Mount",      # Telescope mount power
    2: "Camera",     # Imaging camera power
    3: "Focuser",    # Focuser motor power
    4: "Aux"         # Auxiliary equipment
}

# Default states (True = ON, False = OFF)
DEFAULT_STATES = {
    1: False,  # Mount off by default
    2: False,  # Camera off by default
    3: False,  # Focuser off by default
    4: False   # Aux off by default
}

# Safety settings
EMERGENCY_STOP_ALL = True  # Whether emergency stop turns off all relays
AUTO_RECONNECT = True      # Automatically reconnect on connection loss
RECONNECT_DELAY = 5        # Seconds between reconnection attempts
MAX_RECONNECT_ATTEMPTS = 10

## MQTT Integration (optional)
MQTT_ENABLED = True
MQTT_BROKER = "192.168.1.49"
MQTT_PORT = 1883
MQTT_STATUS_TOPIC = "obsybox/relays/status"
MQTT_COMMAND_TOPIC = "obsybox/relays/command"

## Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "obsyswitch.log"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

## ASCOM Integration
ASCOM_DEVICE_NAME = "ObsyBox.Switch"
ASCOM_DESCRIPTION = "Observatory relay switch controller"
ASCOM_DRIVER_VERSION = "1.0.0"
ASCOM_INTERFACE_VERSION = 2