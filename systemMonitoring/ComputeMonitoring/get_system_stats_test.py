#!/usr/bin/env python3
"""Test sender: publish system stats repeatedly for testing.

Usage:
  python get_system_stats_test.py --interval 1 --count 0

Defaults: interval=1 second, count=0 (run until Ctrl-C)
"""
import argparse
import json
import sys
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description='Publish system stats repeatedly for testing')
    ap.add_argument('--interval', '-i', type=float, default=1.0, help='Seconds between publishes')
    ap.add_argument('--count', '-c', type=int, default=0, help='Number of publishes (0 = infinite)')
    ap.add_argument('--drive', '-d', default='D:', help='Drive letter to report free space for')
    args = ap.parse_args()

    # Ensure we can import the local module even if running from repo root
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    try:
        import get_system_stats as g
    except Exception as e:
        print('Failed to import get_system_stats module:', e, file=sys.stderr)
        sys.exit(2)

    sent = 0
    try:
        while True:
            # Build payload using the same logic as get_system_stats.main
            cpu_temp = g.get_cpu_temp()
            cpu_load = g.get_cpu_load()
            disk_free = g.get_disk_free_gb(args.drive)
            wifi_percent, wifi_dbm = g.get_wifi_signal()

            payload_obj = {
                'hostname': __import__('socket').gethostname(),
                'cpu_temp_c': cpu_temp,
                'cpu_load': cpu_load,
                'disk_free_gb': disk_free,
                'wifi_signal_percent': wifi_percent,
                'wifi_signal_dbm': wifi_dbm,
            }
            filtered = {k: v for k, v in payload_obj.items() if v is not None}
            payload = json.dumps(filtered, separators=(',', ':'))

            rc = g.publish_json(payload)
            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f'[{ts}] sent #{sent+1} rc={rc} payload_keys={list(filtered.keys())}')

            sent += 1
            if args.count > 0 and sent >= args.count:
                break

            # sleep for the requested interval
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print('\nInterrupted by user, exiting')


if __name__ == '__main__':
    main()
