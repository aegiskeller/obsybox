import serial
import time
import sys
import serial.tools.list_ports

SERIAL_PORT = 'COM3'  # Change to your port, e.g., '/dev/ttyUSB0' on Linux
BAUDRATE = 115200

def check_port_available(port):
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if port not in ports:
        raise IOError(f"Serial port {port} not found. Available ports: {ports}")

def send_command(command):
    check_port_available(SERIAL_PORT)
    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=2) as ser:
        ser.write((command + '\n').encode('utf-8'))
        print(f"Sent: {command}")
        # Read lines for up to 3 seconds or until a result is received
        start = time.time()
        while time.time() - start < 3:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"Received: {line}")
                if "RESULT:STATE" in line or "ERROR" in line:
                    break

def open_shutter():
    send_command("COMMAND:OPEN")

def close_shutter():
    send_command("COMMAND:CLOSE")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].lower() not in ("open", "close"):
        print("Usage: python openClose.py [open|close]")
        sys.exit(1)
    action = sys.argv[1].lower()
    if action == "open":
        print("Opening shutter...")
        open_shutter()
    elif action == "close":
        print("Closing shutter...")
        close_shutter()