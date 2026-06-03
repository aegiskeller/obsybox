import serial
import time
import sys
import serial.tools.list_ports

SERIAL_PORT = 'COM7'  # Change to your port, e.g., '/dev/ttyUSB0' on Linux
BAUDRATE = 9600

def check_port_available(port):
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if port not in ports:
        raise IOError(f"Serial port {port} not found. Available ports: {ports}")

def send_command(command):
    check_port_available(SERIAL_PORT)
    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2) as ser:
        # ESP8266 boards often reboot when serial is opened.
        # If startup logs appear, wait for setup completion before sending commands.
        startup_start = time.time()
        while time.time() - startup_start < 4:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"Startup: {line}")
                if "Setup complete." in line:
                    break
        ser.write((command + '\n').encode('utf-8'))
        print(f"Sent: {command}")
        # Read lines until a terminal response is received or timeout.
        start = time.time()
        while time.time() - start < 4:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"Received: {line}")
                if (
                    "RESULT:STATE" in line
                    or "RESULT:PING:OK" in line
                    or "RESULT:Telescope Dust Cover Firmware" in line
                    or "ERROR" in line
                ):
                    break

def open_shutter():
    send_command("COMMAND:OPEN")

def close_shutter():
    send_command("COMMAND:CLOSE")

def ping_device():
    send_command("COMMAND:PING")

def get_firmware_info():
    send_command("COMMAND:INFO")

def get_state():
    send_command("COMMAND:GETSTATE")

if __name__ == "__main__":
    try:
        if len(sys.argv) < 2 or sys.argv[1].lower() not in ("open", "close", "ping", "info", "getstate"):
            print("Usage: python openClose.py [open|close|ping|info|getstate]")
            sys.exit(1)
        action = sys.argv[1].lower()
        if action == "open":
            print("Opening shutter...")
            open_shutter()
        elif action == "close":
            print("Closing shutter...")
            close_shutter()
        elif action == "ping":
            print("Pinging device...")
            ping_device()
        elif action == "info":
            print("Requesting firmware info...")
            get_firmware_info()
        elif action == "getstate":
            print("Requesting current state...")
            get_state()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(2)