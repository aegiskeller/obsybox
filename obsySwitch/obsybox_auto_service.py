#!/usr/bin/env python3
"""
ObsyBox ASCOM Auto-Start Service
Automatically starts Alpaca server when Arduino is detected
"""
import time
import subprocess
import sys
import signal
import os
from pathlib import Path

# Add the obsySwitch directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from obsyswitch_serial_driver import ObsySwitchSerialController

class ObsyBoxAutoService:
    def __init__(self):
        self.server_process = None
        self.running = True
        self.script_dir = Path(__file__).parent
        
        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        print("\n🛑 Shutting down ObsyBox Auto-Service...")
        self.running = False
        self.stop_server()
        sys.exit(0)
        
    def is_arduino_connected(self):
        """Check if Arduino is connected"""
        try:
            controller = ObsySwitchSerialController()
            connected = controller.connect()
            if connected:
                controller.disconnect()
            return connected
        except Exception as e:
            return False
    
    def start_server(self):
        """Start the Alpaca server"""
        if self.server_process is None:
            try:
                self.server_process = subprocess.Popen([
                    sys.executable, 
                    str(self.script_dir / "alpaca_switch_server.py")
                ], cwd=str(self.script_dir))
                print("🚀 ASCOM Alpaca server started")
            except Exception as e:
                print(f"❌ Failed to start server: {e}")
    
    def stop_server(self):
        """Stop the Alpaca server"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print("🛑 ASCOM Alpaca server stopped")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                print("🔪 ASCOM Alpaca server force killed")
            except Exception as e:
                print(f"❌ Error stopping server: {e}")
            finally:
                self.server_process = None
    
    def is_server_healthy(self):
        """Check if server is running and healthy"""
        if self.server_process is None:
            return False
        
        # Check if process is still alive
        if self.server_process.poll() is not None:
            return False
            
        # Could add HTTP health check here
        return True
    
    def run(self):
        """Main service loop"""
        print("🔧 ObsyBox ASCOM Auto-Service Starting")
        print("📱 Monitoring for Arduino connection...")
        
        arduino_was_connected = False
        
        while self.running:
            arduino_connected = self.is_arduino_connected()
            
            if arduino_connected and not arduino_was_connected:
                print("✅ Arduino detected - starting ASCOM server")
                self.start_server()
                arduino_was_connected = True
                
            elif not arduino_connected and arduino_was_connected:
                print("❌ Arduino disconnected - stopping server")
                self.stop_server()
                arduino_was_connected = False
                
            elif arduino_connected and not self.is_server_healthy():
                print("🔄 Server unhealthy - restarting")
                self.stop_server()
                time.sleep(2)
                self.start_server()
            
            time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    service = ObsyBoxAutoService()
    service.run()