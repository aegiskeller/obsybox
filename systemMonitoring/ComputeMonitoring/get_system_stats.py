#!/usr/bin/env python3
"""Collect system stats and publish to MQTT broker 192.168.1.49 on topic obsybox/system_monitoring.

Fields: hostname, cpu_temp_c, cpu_load, disk_free_gb, wifi_signal_percent, wifi_signal_dbm
Null values are omitted from the published JSON.

Fallbacks:
- Try psutil for CPU load and disk usage.
- Try psutil.sensors_temperatures(), then LHM (http://localhost:8085/data.json) for CPU temp.
- Use `netsh wlan show interfaces` for Wi-Fi signal percent and estimate dBm.
- Publish with paho.mqtt if available, otherwise try mosquitto_pub; if neither, print JSON to stdout.

Runs in continuous loop, publishing every 60 seconds.
"""
import json
import socket
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def get_cpu_load():
    # Prefer Windows WMI measurement via PowerShell one-liner when available (returns Average LoadPercentage)
    if sys.platform.startswith('win'):
        try:
            cmd = [
                'powershell', '-NoProfile', '-Command',
                "Get-WmiObject -Class Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average"
            ]
            p = subprocess.run(cmd, capture_output=True, text=True, check=True)
            out = p.stdout.strip()
            if out:
                # Some locales may include commas; normalize
                out_norm = out.replace(',', '.')
                try:
                    return round(float(out_norm), 1)
                except Exception:
                    pass
        except Exception:
            pass

    # Fallback to psutil if available
    try:
        import psutil
        # cpu_percent with interval=1 to get a measured value
        return round(psutil.cpu_percent(interval=1), 1)
    except Exception:
        return None

def get_cpu_temp():
    # Try psutil sensors first
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            # prefer coretemp or cpu
            for key in ('coretemp', 'cpu_thermal', 'acpitz'):
                if key in temps and temps[key]:
                    return round(temps[key][0].current, 1)
            # otherwise pick first available entry
            for v in temps.values():
                if v:
                    return round(v[0].current, 1)
    except Exception:
        pass

    # Fallback: try LocalHardwareMonitor (LHM) JSON on localhost:8085
    try:
        import requests
        LHM_SERVER_URL = "http://localhost:8085/data.json"
        r = requests.get(LHM_SERVER_URL, timeout=2)
        if r.status_code == 200:
            data = r.json()

            def find_sensor_value(node, target):
                if isinstance(node, dict):
                    if node.get("Text", "") == target:
                        value = node.get("Value", "")
                        if value and isinstance(value, str) and '°C' in value:
                            try:
                                return float(value.replace('°C', '').strip())
                            except Exception:
                                return None
                    for child in node.get("Children", []):
                        res = find_sensor_value(child, target)
                        if res is not None:
                            return res
                elif isinstance(node, list):
                    for item in node:
                        res = find_sensor_value(item, target)
                        if res is not None:
                            return res
                return None

            t = find_sensor_value(data, "CPU Package")
            if t is not None:
                return round(t, 1)
    except Exception:
        pass

    return None

def get_disk_usage_percent(drive_letter='D:'):
    """Return disk usage percent (0-100) for the given drive_letter.
    Uses psutil if available, otherwise shutil.disk_usage fallback.
    """
    try:
        import psutil
        usage = psutil.disk_usage(drive_letter)
        if usage.total and usage.total > 0:
            used_pct = (usage.total - usage.free) / usage.total * 100.0
            return round(used_pct, 2)
        return None
    except Exception:
        # fallback to shutil.disk_usage
        try:
            root = drive_letter if drive_letter.endswith('\\') or drive_letter.endswith('/') else (drive_letter + '\\')
            usage = shutil.disk_usage(root)
            if usage.total and usage.total > 0:
                used_pct = (usage.total - usage.free) / usage.total * 100.0
                return round(used_pct, 2)
            return None
        except Exception:
            return None


def get_disk_free_gb(drive_letter='D:'):
    """Return free space in GB for the given drive letter, or None if unavailable."""
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
                # Format: Signal : 78%
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

def publish_json(payload_json: str):
    # Try paho.mqtt
    try:
        import paho.mqtt.publish as publish
        publish.single('obsybox/system_monitoring', payload_json, hostname='192.168.1.49', qos=1)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] Published to MQTT')
        return 0
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] paho.mqtt failed: {e}')

    # Try mosquitto_pub
    try:
        subprocess.run(['mosquitto_pub', '-h', '192.168.1.49', '-t', 'obsybox/system_monitoring', '-m', payload_json], check=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] Published via mosquitto_pub')
        return 0
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f'[{timestamp}] mosquitto_pub failed: {e}')

    # Fallback: print to stdout
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] MQTT unavailable, payload: {payload_json}')
    return 2

def collect_and_publish(drive):
    """Collect system stats and publish to MQTT."""
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

    # Drop keys with None values
    filtered = {k: v for k, v in result.items() if v is not None}

    payload = json.dumps(filtered, separators=(',', ':'))
    return publish_json(payload)

def main(argv):
    # Auto-detect drive based on hostname, with command line override
    hostname = socket.gethostname().lower()
    
    # Define drive mappings per hostname
    drive_mappings = {
        'piglet': 'C:',
        # Add other hostnames here as needed
        # 'othermachine': 'D:',
    }
    
    # Default to D: for unmapped machines
    drive = drive_mappings.get(hostname, 'D:')
    
    # Command line argument overrides auto-detection
    if len(argv) >= 2:
        drive = argv[1]

    print(f'Starting system monitoring loop for {hostname} (monitoring drive {drive})')
    print('Publishing to obsybox/system_monitoring every 60 seconds')
    print('Press Ctrl+C to stop\n')

    while True:
        try:
            collect_and_publish(drive)
            time.sleep(60)
        except KeyboardInterrupt:
            print('\nStopping system monitoring...')
            sys.exit(0)
        except Exception as e:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f'[{timestamp}] Error: {e}')
            time.sleep(60)  # Continue despite errors

if __name__ == '__main__':
    main(sys.argv)
