#!/usr/bin/env python3
"""
ASCOM Switch Server for ObsyBox Relay Controller

This creates an ASCOM-compatible server that NINA and other astronomy software
can connect to as a standard ASCOM Switch device.

Usage:
    1. Run this script: python ascom_switch_server.py
    2. Configure NINA to use "ASCOM Switch" 
    3. Set server address to: localhost:8080
    4. Control relays through NINA's switch interface

Requirements:
    pip install flask
"""

from flask import Flask, jsonify, request
import json
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from obsyswitch_serial_driver import ObsySwitchSerialController
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure obsyswitch_serial_driver.py is in the same directory")
    sys.exit(1)

app = Flask(__name__)

# Global controller instance
controller = None
device_info = {
    "Name": "ObsyBox Relay Switch",
    "Description": "Arduino-based relay controller for observatory equipment",
    "DriverVersion": "1.0.0",
    "InterfaceVersion": 2,
    "SupportedActions": ["Emergency_Stop", "Test_Connection"]
}

def get_controller():
    """Get or create controller instance"""
    global controller
    if controller is None:
        controller = ObsySwitchSerialController()
    return controller

@app.route('/api/v1/switch/0/connected', methods=['GET'])
def get_connected():
    """ASCOM Connected property"""
    ctrl = get_controller()
    return jsonify({"Value": ctrl.is_connected()})

@app.route('/api/v1/switch/0/connected', methods=['PUT'])
def set_connected():
    """ASCOM Connected property setter"""
    data = request.get_json()
    connected = data.get('Connected', False)
    
    ctrl = get_controller()
    
    if connected:
        success = ctrl.connect()
        if success:
            return jsonify({"Value": True})
        else:
            return jsonify({"ErrorNumber": 1024, "ErrorMessage": "Failed to connect to Arduino"}), 500
    else:
        ctrl.disconnect()
        return jsonify({"Value": False})

@app.route('/api/v1/switch/0/maxswitch', methods=['GET'])
def get_max_switch():
    """ASCOM MaxSwitch property"""
    ctrl = get_controller()
    return jsonify({"Value": ctrl.get_max_switch()})

@app.route('/api/v1/switch/0/getswitch/<int:switch_id>', methods=['GET'])
def get_switch_state(switch_id):
    """ASCOM GetSwitch method"""
    ctrl = get_controller()
    
    if not ctrl.is_connected():
        return jsonify({"ErrorNumber": 1025, "ErrorMessage": "Not connected to device"}), 500
    
    try:
        state = ctrl.get_switch(switch_id)
        return jsonify({"Value": state})
    except Exception as e:
        return jsonify({"ErrorNumber": 1026, "ErrorMessage": str(e)}), 500

@app.route('/api/v1/switch/0/setswitch/<int:switch_id>', methods=['PUT'])
def set_switch_state(switch_id):
    """ASCOM SetSwitch method"""
    data = request.get_json()
    state = data.get('State', False)
    
    ctrl = get_controller()
    
    if not ctrl.is_connected():
        return jsonify({"ErrorNumber": 1025, "ErrorMessage": "Not connected to device"}), 500
    
    try:
        success = ctrl.set_switch(switch_id, state)
        if success:
            return jsonify({"Value": state})
        else:
            return jsonify({"ErrorNumber": 1027, "ErrorMessage": f"Failed to set switch {switch_id}"}), 500
    except Exception as e:
        return jsonify({"ErrorNumber": 1028, "ErrorMessage": str(e)}), 500

@app.route('/api/v1/switch/0/getswitchname/<int:switch_id>', methods=['GET'])
def get_switch_name(switch_id):
    """ASCOM GetSwitchName method"""
    ctrl = get_controller()
    name = ctrl.get_switch_name(switch_id)
    return jsonify({"Value": name})

@app.route('/api/v1/switch/0/canwrite/<int:switch_id>', methods=['GET'])
def can_write(switch_id):
    """ASCOM CanWrite method"""
    ctrl = get_controller()
    can_write = ctrl._validate_switch_id(switch_id)
    return jsonify({"Value": can_write})

@app.route('/api/v1/switch/0/description', methods=['GET'])
def get_description():
    """ASCOM Description property"""
    return jsonify({"Value": device_info["Description"]})

@app.route('/api/v1/switch/0/name', methods=['GET'])
def get_name():
    """ASCOM Name property"""
    return jsonify({"Value": device_info["Name"]})

@app.route('/api/v1/switch/0/driverversion', methods=['GET'])
def get_driver_version():
    """ASCOM DriverVersion property"""
    return jsonify({"Value": device_info["DriverVersion"]})

@app.route('/api/v1/switch/0/interfaceversion', methods=['GET'])
def get_interface_version():
    """ASCOM InterfaceVersion property"""
    return jsonify({"Value": device_info["InterfaceVersion"]})

@app.route('/api/v1/switch/0/supportedactions', methods=['GET'])
def get_supported_actions():
    """ASCOM SupportedActions property"""
    return jsonify({"Value": device_info["SupportedActions"]})

@app.route('/api/v1/switch/0/action', methods=['PUT'])
def device_action():
    """ASCOM Action method"""
    data = request.get_json()
    action = data.get('Action', '')
    parameters = data.get('Parameters', '')
    
    ctrl = get_controller()
    
    if action == "Emergency_Stop":
        if ctrl.is_connected():
            success = ctrl.emergency_stop()
            return jsonify({"Value": "Emergency stop executed" if success else "Emergency stop failed"})
        else:
            return jsonify({"ErrorNumber": 1025, "ErrorMessage": "Not connected to device"}), 500
    
    elif action == "Test_Connection":
        if ctrl.is_connected():
            success = ctrl.ping()
            return jsonify({"Value": "Connection OK" if success else "Connection failed"})
        else:
            return jsonify({"Value": "Not connected"})
    
    else:
        return jsonify({"ErrorNumber": 1029, "ErrorMessage": f"Unsupported action: {action}"}), 400

@app.route('/status', methods=['GET'])
def status():
    """Status page for debugging"""
    ctrl = get_controller()
    
    status_info = {
        "connected": ctrl.is_connected(),
        "device_info": device_info,
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
            status_info["switches"][i] = {
                "name": ctrl.get_switch_name(i),
                "state": ctrl.get_switch(i) if ctrl.is_connected() else False,
                "can_write": ctrl._validate_switch_id(i)
            }
    
    return jsonify(status_info)

@app.route('/', methods=['GET'])
def home():
    """Home page with control interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ObsyBox ASCOM Switch Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .status { padding: 20px; border: 1px solid #ccc; border-radius: 8px; margin: 20px 0; }
            .switch { padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
            .on { background-color: #d4edda; }
            .off { background-color: #f8d7da; }
            button { padding: 8px 16px; margin: 4px; border: none; border-radius: 4px; cursor: pointer; }
            .btn-on { background-color: #28a745; color: white; }
            .btn-off { background-color: #dc3545; color: white; }
            .btn-connect { background-color: #007bff; color: white; }
            .btn-emergency { background-color: #fd7e14; color: white; font-weight: bold; }
        </style>
        <script>
            async function connect() {
                const response = await fetch('/api/v1/switch/0/connected', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({Connected: true})
                });
                location.reload();
            }
            
            async function disconnect() {
                const response = await fetch('/api/v1/switch/0/connected', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({Connected: false})
                });
                location.reload();
            }
            
            async function setSwitch(id, state) {
                const response = await fetch(`/api/v1/switch/0/setswitch/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({State: state})
                });
                location.reload();
            }
            
            async function emergencyStop() {
                const response = await fetch('/api/v1/switch/0/action', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({Action: 'Emergency_Stop', Parameters: ''})
                });
                location.reload();
            }
        </script>
    </head>
    <body>
        <h1> ObsyBox ASCOM Switch Server</h1>
        <p>This is the web interface for your Arduino relay controller ASCOM driver.</p>
        
        <div class="status">
            <h2>Server Status</h2>
            <p><strong>Server Address:</strong> http://localhost:8080</p>
            <p><strong>ASCOM API:</strong> http://localhost:8080/api/v1/switch/0/</p>
            <p><strong>Status Endpoint:</strong> <a href="/status">/status</a></p>
        </div>
        
        <div class="status">
            <h2>Connection Control</h2>
            <button class="btn-connect" onclick="connect()">Connect to Arduino</button>
            <button class="btn-off" onclick="disconnect()">Disconnect</button>
            <button class="btn-emergency" onclick="emergencyStop()"> EMERGENCY STOP</button>
        </div>
        
        <div class="status">
            <h2>NINA Integration</h2>
            <p><strong>For NINA ASCOM Setup:</strong></p>
            <ol>
                <li>In NINA, go to Equipment  Switch</li>
                <li>Select "ASCOM Switch" as device type</li>
                <li>Configure server: <code>http://localhost:8080</code></li>
                <li>Test connection and use switches in sequences</li>
            </ol>
        </div>
        
        <p><em>Refresh page to update status  Use /status endpoint for JSON data</em></p>
    </body>
    </html>
    '''

def main():
    """Main server startup"""
    print(f"Starting ObsyBox ASCOM Switch Server")
    print("=" * 50)
    print(f"Server URL: http://localhost:8080")
    print(f"ASCOM API: http://localhost:8080/api/v1/switch/0/")
    print(f"Status: http://localhost:8080/status")
    print(f"Stop server: Ctrl+C")
    print("=" * 50)
    print()
    print(f"NINA Setup Instructions:")
    print("1. Equipment  Switch  ASCOM Switch")
    print("2. Server: http://localhost:8080") 
    print("3. Test connection")
    print("4. Use switches in sequences")
    print()
    
    try:
        # Start the Flask server
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("\nServer stopped")
        if controller:
            controller.disconnect()

if __name__ == "__main__":
    main()