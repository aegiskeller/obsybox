#!/usr/bin/env python3
"""Test script to show what would be sent to MQTT without actually sending it."""

import json
import socket
import shutil
import subprocess
import sys
from pathlib import Path

# Import the functions from the main script
sys.path.append(str(Path(__file__).parent))

def get_cpu_load():
    if sys.platform.startswith('win'):
        try:
            cmd = [
                'powershell', '-NoProfile', '-Command',
                "Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average"
            ]
            p = subprocess.run(cmd, capture_output=True, text=True, check=True)
            out = p.stdout.strip()
            if out:
                out_norm = out.replace(',', '.')
                try:
                    return round(float(out_norm), 1)
                except Exception:
                    pass
        except Exception:
            pass
    
    try:
        import psutil
        return round(psutil.cpu_percent(interval=1), 1)
    except Exception:
        return None

def get_cpu_temp():
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            for key in ('coretemp', 'cpu_thermal', 'acpitz'):
                if key in temps and temps[key]:
                    return round(temps[key][0].current, 1)
            for v in temps.values():
                if v:
                    return round(v[0].current, 1)
    except Exception:
        pass
    return None

def get_disk_free_gb(drive_letter='C:'):
    try:
        import psutil
        usage = psutil.disk_usage(drive_letter)
        free_gb = round(usage.free / (1024 ** 3), 2)
        return free_gb
    except Exception:
        try:
            root = drive_letter if drive_letter.endswith('\\') or drive_letter.endswith('/') else (drive_letter + '\\')
            usage = shutil.disk_usage(root)
            free_gb = round(usage.free / (1024 ** 3), 2)
            return free_gb
        except Exception:
            return None

def get_wifi_signal():
    try:
        p = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, check=False)
        out = p.stdout
        if not out:
            return None, None
        for line in out.splitlines():
            line = line.strip()
            if line.lower().startswith('signal'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    raw = parts[1].strip().rstrip('%')
                    if raw.isdigit():
                        percent = int(raw)
                        dbm = round((percent / 2.0) - 100)
                        return percent, int(dbm)
        return None, None
    except Exception:
        return None, None

def main():
    # Auto-detect drive based on hostname
    hostname = socket.gethostname().lower()
    drive_mappings = {
        'piglet': 'C:',
    }
    drive = drive_mappings.get(hostname, 'D:')
    
    print(f"🖥️  System Stats for: {socket.gethostname()}")
    print(f"💾 Monitoring drive: {drive}")
    print("=" * 50)
    
    cpu_temp = get_cpu_temp()
    cpu_load = get_cpu_load()
    disk_free_gb = get_disk_free_gb(drive)
    wifi_percent, wifi_dbm = get_wifi_signal()

    result = {
        'hostname': socket.gethostname(),
        'cpu_temp_c': cpu_temp,
        'cpu_load': cpu_load,
        'disk_free_gb': disk_free_gb,
        'wifi_signal_percent': wifi_percent,
        'wifi_signal_dbm': wifi_dbm,
    }

    # Show individual values
    for key, value in result.items():
        if value is not None:
            if key == 'cpu_temp_c':
                print(f"🌡️  CPU Temperature: {value}°C")
            elif key == 'cpu_load':
                print(f"⚡ CPU Load: {value}%")
            elif key == 'disk_free_gb':
                print(f"💽 Disk Free ({drive}): {value} GB")
            elif key == 'wifi_signal_percent':
                print(f"📶 WiFi Signal: {value}%")
            elif key == 'wifi_signal_dbm':
                print(f"📡 WiFi Signal: {value} dBm")
            elif key == 'hostname':
                print(f"🏷️  Hostname: {value}")
        else:
            print(f"❌ {key}: Not available")
    
    # Filter out None values
    filtered = {k: v for k, v in result.items() if v is not None}
    
    print("\n" + "=" * 50)
    print("📤 MQTT Message that WOULD be sent:")
    print(f"📍 Topic: obsybox/system_monitoring")
    print(f"📦 Payload: {json.dumps(filtered, separators=(',', ':'))}")
    print("=" * 50)

if __name__ == '__main__':
    main()