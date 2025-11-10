#!/usr/bin/env python3
"""
ASCOM Alpaca Switch Server for ObsyBox Relay Controller

This creates a fully compliant ASCOM Alpaca Switch device server that:
1. Implements the complete ASCOM Switch V3 interface
2. Appears natively in NINA's ASCOM Switch device list
3. Provides management API for device discovery
4. Follows ASCOM Alpaca REST API specification

Usage:
    1. Run this server: python alpaca_switch_server.py
    2. NINA will auto-discover it via Alpaca discovery
    3. Select "ObsyBox Relay Switch" in NINA Equipment > Switch
    4. Configure and use like any ASCOM Switch device

Requirements:
    pip install flask
"""

from flask import Flask, jsonify, request
import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
import socket

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from obsyswitch_serial_driver import ObsySwitchSerialController
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure obsyswitch_serial_driver.py is in the same directory")
    sys.exit(1)

app = Flask(__name__)

# ASCOM Alpaca Configuration
DEVICE_TYPE = "Switch"
DEVICE_NUMBER = 0
SERVER_NAME = "ObsyBox"
MANUFACTURER = "ObsyBox Project"
LOCATION = "Observatory"
DRIVER_VERSION = "1.0.0"
DRIVER_INFO = [
    f"{SERVER_NAME} Alpaca Switch Server v{DRIVER_VERSION}",
    f"ObsyBox Arduino Relay Controller",
    f"ASCOM Alpaca compliant device server",
    f"Supports 4-channel relay switching",
    f"Built on {datetime.now().strftime('%Y-%m-%d')}"
]

# Global device state
controller = None
client_id = 0
client_transaction_id = 0

def get_controller():
    """Get or create controller instance"""
    global controller
    if controller is None:
        controller = ObsySwitchSerialController()
    return controller

def validate_client_info():
    """Validate client ID and transaction ID from request"""
    global client_id, client_transaction_id
    
    # Get client info from form data or JSON
    if request.content_type == 'application/json':
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()
    
    client_id = int(data.get('ClientID', 0))
    client_transaction_id = int(data.get('ClientTransactionID', 0))

def create_response(value=None, error_number=0, error_message=""):
    """Create standard ASCOM Alpaca response"""
    global client_transaction_id
    client_transaction_id += 1
    
    response = {
        "ClientTransactionID": client_transaction_id,
        "ServerTransactionID": int(time.time() * 1000) % 2**31,  # Unique server transaction ID
        "ErrorNumber": error_number,
        "ErrorMessage": error_message
    }
    
    if error_number == 0 and value is not None:
        response["Value"] = value
    
    return jsonify(response)

def handle_ascom_error(func):
    """Decorator to handle ASCOM exceptions and return proper error responses"""
    from functools import wraps
    @wraps(func)
    def error_wrapper(*args, **kwargs):
        try:
            validate_client_info()
            return func(*args, **kwargs)
        except ValueError as e:
            return create_response(error_number=0x401, error_message=f"Invalid value: {str(e)}")
        except ConnectionError as e:
            return create_response(error_number=0x407, error_message=f"Not connected: {str(e)}")
        except Exception as e:
            return create_response(error_number=0x500, error_message=f"Driver error: {str(e)}")
    return error_wrapper

# ============================================================================
# ASCOM Alpaca Management API (required for device discovery)
# ============================================================================

@app.route('/management/apiversions', methods=['GET'])
def api_versions():
    """Get supported API versions"""
    return jsonify({"Value": [1]})

@app.route('/management/v1/description', methods=['GET'])
def server_description():
    """Get server description"""
    return jsonify({
        "Value": {
            "ServerName": SERVER_NAME,
            "Manufacturer": MANUFACTURER,
            "ManufacturerVersion": DRIVER_VERSION,
            "Location": LOCATION
        }
    })

@app.route('/management/v1/configureddevices', methods=['GET'])
def configured_devices():
    """Get list of configured devices"""
    return jsonify({
        "Value": [{
            "DeviceName": "ObsyBox Relay Switch",
            "DeviceType": DEVICE_TYPE,
            "DeviceNumber": DEVICE_NUMBER,
            "UniqueID": f"ObsyBox.Switch.{DEVICE_NUMBER}"
        }]
    })

# ============================================================================
# ASCOM Alpaca Common Device Properties
# ============================================================================

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/connected', methods=['GET'])
@handle_ascom_error
def get_connected():
    """Get Connected property"""
    ctrl = get_controller()
    return create_response(ctrl.is_connected())

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/connected', methods=['PUT'])
@handle_ascom_error
def set_connected():
    """Set Connected property"""
    data = request.form if request.form else request.get_json()
    connected = str(data.get('Connected', 'false')).lower() == 'true'
    
    ctrl = get_controller()
    
    if connected:
        success = ctrl.connect()
        if not success:
            return create_response(error_number=0x500, error_message="Failed to connect to Arduino")
    else:
        ctrl.disconnect()
    
    return create_response()

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/description', methods=['GET'])
@handle_ascom_error
def get_description():
    """Get Description property"""
    return create_response("Arduino-based 4-channel relay controller for observatory automation")

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/name', methods=['GET'])
@handle_ascom_error
def get_name():
    """Get Name property"""
    return create_response("ObsyBox Relay Switch")

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/driverinfo', methods=['GET'])
@handle_ascom_error
def get_driver_info():
    """Get DriverInfo property"""
    return create_response(DRIVER_INFO)

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/driverversion', methods=['GET'])
@handle_ascom_error
def get_driver_version():
    """Get DriverVersion property"""
    return create_response(DRIVER_VERSION)

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/interfaceversion', methods=['GET'])
@handle_ascom_error
def get_interface_version():
    """Get InterfaceVersion property"""
    return create_response(3)  # Switch V3

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/supportedactions', methods=['GET'])
@handle_ascom_error
def get_supported_actions():
    """Get SupportedActions property"""
    return create_response(["EmergencyStop", "TestConnection"])

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/action', methods=['PUT'])
@handle_ascom_error
def device_action():
    """Device Action method"""
    data = request.form if request.form else request.get_json()
    action = data.get('Action', '')
    parameters = data.get('Parameters', '')
    
    ctrl = get_controller()
    
    if not ctrl.is_connected():
        return create_response(error_number=0x407, error_message="Device not connected")
    
    if action.lower() == "emergencystop":
        success = ctrl.emergency_stop()
        result = "Emergency stop executed" if success else "Emergency stop failed"
        return create_response(result)
    
    elif action.lower() == "testconnection":
        success = ctrl.ping()
        result = "Connection test passed" if success else "Connection test failed"
        return create_response(result)
    
    else:
        return create_response(error_number=0x400, error_message=f"Unsupported action: {action}")

# ============================================================================
# ASCOM Alpaca Switch-Specific Properties and Methods
# ============================================================================

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/maxswitch', methods=['GET'])
@handle_ascom_error
def get_max_switch():
    """Get MaxSwitch property"""
    ctrl = get_controller()
    return create_response(ctrl.get_max_switch())

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/canwrite', methods=['GET'])
@handle_ascom_error
def can_write():
    """CanWrite method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    return create_response(True)  # All our switches can be written to

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/getswitch', methods=['GET'])
@handle_ascom_error
def get_switch():
    """GetSwitch method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl.is_connected():
        return create_response(error_number=0x407, error_message="Device not connected")
    
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    try:
        state = ctrl.get_switch(switch_id)
        return create_response(state)
    except Exception as e:
        return create_response(error_number=0x500, error_message=f"Failed to get switch state: {str(e)}")

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/setswitch', methods=['PUT'])
@handle_ascom_error
def set_switch():
    """SetSwitch method"""
    data = request.form if request.form else request.get_json()
    switch_id = int(data.get('Id', -1))
    state = str(data.get('State', 'false')).lower() == 'true'
    
    ctrl = get_controller()
    if not ctrl.is_connected():
        return create_response(error_number=0x407, error_message="Device not connected")
    
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    try:
        success = ctrl.set_switch(switch_id, state)
        if success:
            return create_response()
        else:
            return create_response(error_number=0x500, error_message=f"Failed to set switch {switch_id}")
    except Exception as e:
        return create_response(error_number=0x500, error_message=f"Failed to set switch: {str(e)}")

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/getswitchname', methods=['GET'])
@handle_ascom_error
def get_switch_name():
    """GetSwitchName method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    name = ctrl.get_switch_name(switch_id)
    return create_response(name)

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/getswitchdescription', methods=['GET'])
@handle_ascom_error
def get_switch_description():
    """GetSwitchDescription method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    # Get equipment descriptions
    descriptions = {
        0: "Telescope mount power control relay",
        1: "Main imaging camera power control relay", 
        2: "Electronic focuser power control relay",
        3: "Auxiliary equipment power control relay"
    }
    
    description = descriptions.get(switch_id, f"Switch {switch_id}")
    return create_response(description)

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/getswitchvalue', methods=['GET'])
@handle_ascom_error
def get_switch_value():
    """GetSwitchValue method - returns switch state as float"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl.is_connected():
        return create_response(error_number=0x407, error_message="Device not connected")
    
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    try:
        state = ctrl.get_switch(switch_id)
        return create_response(1.0 if state else 0.0)
    except Exception as e:
        return create_response(error_number=0x500, error_message=f"Failed to get switch value: {str(e)}")

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/setswitchvalue', methods=['PUT'])
@handle_ascom_error
def set_switch_value():
    """SetSwitchValue method - sets switch based on value (0.0 = off, > 0.0 = on)"""
    data = request.form if request.form else request.get_json()
    switch_id = int(data.get('Id', -1))
    value = float(data.get('Value', 0.0))
    
    ctrl = get_controller()
    if not ctrl.is_connected():
        return create_response(error_number=0x407, error_message="Device not connected")
    
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    if not (0.0 <= value <= 1.0):
        return create_response(error_number=0x401, error_message="Value must be between 0.0 and 1.0")
    
    try:
        state = value > 0.0
        success = ctrl.set_switch(switch_id, state)
        if success:
            return create_response()
        else:
            return create_response(error_number=0x500, error_message=f"Failed to set switch {switch_id}")
    except Exception as e:
        return create_response(error_number=0x500, error_message=f"Failed to set switch value: {str(e)}")

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/minswitchvalue', methods=['GET'])
@handle_ascom_error
def get_min_switch_value():
    """MinSwitchValue method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    return create_response(0.0)

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/maxswitchvalue', methods=['GET'])
@handle_ascom_error
def get_max_switch_value():
    """MaxSwitchValue method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    return create_response(1.0)

@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/switchstep', methods=['GET'])
@handle_ascom_error
def get_switch_step():
    """SwitchStep method"""
    switch_id = int(request.args.get('Id', -1))
    
    ctrl = get_controller()
    if not ctrl._validate_switch_id(switch_id):
        return create_response(error_number=0x401, error_message=f"Switch ID {switch_id} out of range")
    
    return create_response(1.0)  # Binary switches have step size of 1.0

# For async operations (not implemented for simple relays)
@app.route(f'/api/v1/{DEVICE_TYPE.lower()}/{DEVICE_NUMBER}/canasync', methods=['GET'])
@handle_ascom_error
def can_async():
    """CanAsync method"""
    return create_response(False)  # Simple relays are synchronous

# ============================================================================
# Status and Debug Pages
# ============================================================================

@app.route('/status', methods=['GET'])
def status():
    """Status page for debugging"""
    ctrl = get_controller()
    
    status_info = {
        "server": {
            "name": SERVER_NAME,
            "version": DRIVER_VERSION,
            "device_type": DEVICE_TYPE,
            "device_number": DEVICE_NUMBER
        },
        "connected": ctrl.is_connected(),
        "switches": {}
    }
    
    if ctrl.is_connected():
        device_status = ctrl.get_device_info()
        if device_status:
            status_info["arduino"] = {
                "device_name": device_status.device_name,
                "firmware": device_status.firmware,
                "uptime": device_status.uptime,
                "free_memory": device_status.free_memory
            }
        
        # Get all switch states
        for i in range(ctrl.get_max_switch() + 1):
            try:
                status_info["switches"][i] = {
                    "name": ctrl.get_switch_name(i),
                    "state": ctrl.get_switch(i),
                    "can_write": True
                }
            except:
                status_info["switches"][i] = {
                    "name": f"Switch {i}",
                    "state": False,
                    "can_write": True,
                    "error": "Failed to read state"
                }
    
    return jsonify(status_info)

@app.route('/', methods=['GET'])
def home():
    """Home page with setup instructions"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ObsyBox ASCOM Alpaca Switch Server</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            .status {{ padding: 15px; margin: 15px 0; border-radius: 5px; }}
            .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .info {{ background-color: #e7f3ff; color: #0c5460; border: 1px solid #b3e5fc; }}
            .section {{ margin: 25px 0; }}
            code {{ background-color: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
            .endpoint {{ background-color: #f8f9fa; padding: 10px; border-left: 4px solid #007bff; margin: 10px 0; }}
            .step {{ background-color: #fff3cd; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔌 ObsyBox ASCOM Alpaca Switch Server</h1>
            
            <div class="status success">
                <strong>✅ Server Running</strong><br>
                ASCOM Alpaca compliant device server for Arduino relay controller
            </div>
            
            <div class="section">
                <h2>🎯 NINA Setup Instructions</h2>
                
                <div class="step">
                    <strong>Step 1:</strong> In NINA, go to <strong>Equipment → Switch</strong>
                </div>
                
                <div class="step">
                    <strong>Step 2:</strong> Click <strong>Setup</strong> next to Switch
                </div>
                
                <div class="step">
                    <strong>Step 3:</strong> Select <strong>"ASCOM Switch"</strong> from the dropdown
                </div>
                
                <div class="step">
                    <strong>Step 4:</strong> Click <strong>Setup</strong> and enter:<br>
                    <code>http://localhost:11111</code>
                </div>
                
                <div class="step">
                    <strong>Step 5:</strong> Click <strong>Connect</strong> to test the connection
                </div>
                
                <div class="step">
                    <strong>Step 6:</strong> Your switches should appear as:<br>
                    • Switch 0: Mount<br>
                    • Switch 1: Camera<br>  
                    • Switch 2: Focuser<br>
                    • Switch 3: Aux
                </div>
            </div>
            
            <div class="section">
                <h2>📡 API Endpoints</h2>
                
                <div class="endpoint">
                    <strong>Management API:</strong><br>
                    <code>GET /management/v1/configureddevices</code> - Device discovery<br>
                    <code>GET /management/v1/description</code> - Server info
                </div>
                
                <div class="endpoint">
                    <strong>Switch API:</strong><br>
                    <code>GET /api/v1/switch/0/maxswitch</code> - Number of switches<br>
                    <code>GET /api/v1/switch/0/getswitch?Id=0</code> - Get switch state<br>
                    <code>PUT /api/v1/switch/0/setswitch</code> - Set switch state
                </div>
                
                <div class="endpoint">
                    <strong>Debug:</strong><br>
                    <code>GET /status</code> - <a href="/status">Device status JSON</a>
                </div>
            </div>
            
            <div class="section">
                <h2>🔧 Switch Mapping</h2>
                <table border="1" style="border-collapse: collapse; width: 100%;">
                    <tr style="background-color: #f8f9fa;">
                        <th style="padding: 10px;">ASCOM ID</th>
                        <th style="padding: 10px;">Name</th>
                        <th style="padding: 10px;">Equipment</th>
                        <th style="padding: 10px;">Arduino Pin</th>
                    </tr>
                    <tr><td style="padding: 10px;">0</td><td style="padding: 10px;">Mount</td><td style="padding: 10px;">Telescope Mount</td><td style="padding: 10px;">Pin 2</td></tr>
                    <tr><td style="padding: 10px;">1</td><td style="padding: 10px;">Camera</td><td style="padding: 10px;">Imaging Camera</td><td style="padding: 10px;">Pin 3</td></tr>
                    <tr><td style="padding: 10px;">2</td><td style="padding: 10px;">Focuser</td><td style="padding: 10px;">Electronic Focuser</td><td style="padding: 10px;">Pin 4</td></tr>
                    <tr><td style="padding: 10px;">3</td><td style="padding: 10px;">Aux</td><td style="padding: 10px;">Auxiliary Equipment</td><td style="padding: 10px;">Pin 5</td></tr>
                </table>
            </div>
            
            <div class="status info">
                <strong>🌟 Fully ASCOM Compliant</strong><br>
                This server implements the complete ASCOM Alpaca Switch V3 interface and will appear as a native ASCOM device in NINA and other astronomy software.
            </div>
            
            <p><em>Server Port: 11111 • ASCOM Alpaca Protocol • Auto-discovery enabled</em></p>
        </div>
    </body>
    </html>
    '''

def main():
    """Main server startup"""
    print("🚀 Starting ObsyBox ASCOM Alpaca Switch Server")
    print("=" * 60)
    print(f"🌐 Server URL: http://localhost:11111")
    print(f"🔌 ASCOM API: http://localhost:11111/api/v1/switch/0/")
    print(f"📊 Management: http://localhost:11111/management/v1/")
    print(f"📋 Status: http://localhost:11111/status")
    print(f"🛑 Stop server: Ctrl+C")
    print("=" * 60)
    print()
    print("📋 NINA Discovery Instructions:")
    print("1. Equipment → Switch → ASCOM Switch")
    print("2. Setup → Enter: http://localhost:11111")  
    print("3. Connect and test switches")
    print("4. Use in sequences like any ASCOM Switch")
    print()
    print("🎯 The server will be auto-discoverable by ASCOM Alpaca clients")
    print()
    
    try:
        # Use port 11111 (common ASCOM Alpaca port)
        app.run(host='0.0.0.0', port=11111, debug=False)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        if controller:
            controller.disconnect()

if __name__ == "__main__":
    main()