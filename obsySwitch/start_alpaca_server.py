#!/usr/bin/env python3
"""
ObsyBox ASCOM Alpaca Switch Server Launcher

This script starts the ASCOM Alpaca Switch server for the ObsyBox relay controller.
The server makes the Arduino relay controller appear as a native ASCOM Switch device
in NINA and other ASCOM clients.

Usage:
    python start_alpaca_server.py

Features:
    - Auto-detection of Arduino on USB Serial ports
    - Full ASCOM Alpaca Switch V3 compliance  
    - Native integration with NINA
    - Web-based management interface
    - Proper ASCOM error handling and logging

The server will run on http://localhost:11111 and be auto-discoverable by ASCOM clients.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def check_requirements():
    """Check if required dependencies are installed"""
    try:
        import flask
        import serial
        print("✅ Required packages (flask, pyserial) are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Install with: pip install flask pyserial")
        return False

def check_arduino_connection():
    """Check if Arduino is connected and responding"""
    try:
        # Import the serial driver to test connection
        sys.path.insert(0, str(Path(__file__).parent))
        from obsyswitch_serial_driver import ObsySwitchSerialController
        
        print("🔍 Checking Arduino connection...")
        controller = ObsySwitchSerialController()
        
        if controller.connect():
            print(f"✅ Arduino connected on {controller.port}")
            controller.disconnect()
            return True
        else:
            print("❌ No Arduino found - check USB connection")
            return False
            
    except Exception as e:
        print(f"❌ Arduino connection test failed: {e}")
        return False

def start_server():
    """Start the Alpaca server"""
    script_path = Path(__file__).parent / "alpaca_switch_server.py"
    
    if not script_path.exists():
        print(f"❌ Server script not found: {script_path}")
        return False
    
    print("🚀 Starting ASCOM Alpaca Switch Server...")
    print("=" * 60)
    
    try:
        # Start the server process
        process = subprocess.Popen([
            sys.executable, str(script_path)
        ], cwd=script_path.parent)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Test if server is responding
        try:
            response = requests.get("http://localhost:11111/status", timeout=5)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                print()
                print("🌐 Server URL: http://localhost:11111")
                print("📊 Management API: http://localhost:11111/management/v1/")
                print("🔌 Switch API: http://localhost:11111/api/v1/switch/0/")
                print("📋 Status: http://localhost:11111/status")
                print()
                print("📋 NINA Integration:")
                print("   1. Equipment → Switch → ASCOM Switch")  
                print("   2. Setup → Enter: http://localhost:11111")
                print("   3. Select 'ObsyBox Relay Switch'")
                print("   4. Connect and test switches")
                print()
                print("🛑 Press Ctrl+C to stop the server")
                print("=" * 60)
                
                # Keep the process running
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print("\n\n🛑 Stopping server...")
                    process.terminate()
                    process.wait()
                    print("✅ Server stopped")
                    
            else:
                print("❌ Server started but not responding correctly")
                process.terminate()
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Server not responding - check for port conflicts")
            process.terminate()
            return False
            
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False
    
    return True

def main():
    """Main launcher function"""
    print("🔧 ObsyBox ASCOM Alpaca Switch Server Launcher")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        return 1
    
    # Check Arduino connection
    if not check_arduino_connection():
        print("\n💡 Troubleshooting tips:")
        print("   • Check USB cable connection")
        print("   • Verify Arduino is programmed with RelayController_Serial.ino")
        print("   • Close Arduino IDE Serial Monitor if open")
        print("   • Try different USB port")
        return 1
    
    # Start the server
    if not start_server():
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())