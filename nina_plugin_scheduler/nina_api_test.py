#!/usr/bin/env python3
"""obsybox NINA API Test - Safe testing with notifications

Simple, safe test script to exercise NINA's read-only API endpoints and
send a few test notifications via the Ground Station plugin. This file
is intentionally conservative (no mount moves) and is a starting point
for working with simulated equipment in NINA.
"""

from datetime import datetime
import json
import time
import sys
import requests
import traceback

# NINA API settings
NINA_API_URL = "http://localhost:1888"
NINA_API_ENDPOINT_CAMERA = "/v2/api/equipment/camera/info"
NINA_API_ENDPOINT_STATUS = "/v2/api/version"
NINA_API_ENDPOINT_MOUNT = "/v2/api/equipment/mount/info"
NINA_API_ENDPOINT_DOME = "/v2/api/equipment/dome/info"


def get_timestamp():
    """Return current timestamp in a readable format."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def query_nina_api(endpoint):
    """Query NINA API at the specified endpoint and return parsed JSON or None."""
    try:
        response = requests.get(f"{NINA_API_URL}{endpoint}", timeout=5)
        response.raise_for_status()  # Raise an exception for HTTP errors
        try:
            return response.json()
        except ValueError:
            # Some endpoints may return plain text; return raw text but log a warning
            text = response.text
            if text:
                print(f"[{get_timestamp()}] Warning: non-JSON response from {endpoint!s}: {text!r}")
            return text
    except requests.exceptions.RequestException as e:
        print(f"[{get_timestamp()}] Error connecting to NINA API: {e}")
        return None


# Cache plugin detection to avoid repeated failing POSTs
_groundstation_checked = False
_has_groundstation = False


def check_groundstation_plugin():
    """Return True if a Ground Station / notification plugin appears available.

    This queries `/v2/api/plugins` and heuristically searches the response for
    plugin names or values that contain 'ground', 'station' or 'notification'.
    The result is cached for the lifetime of the process.
    """
    global _groundstation_checked, _has_groundstation
    if _groundstation_checked:
        return _has_groundstation

    _groundstation_checked = True
    resp = query_nina_api("/v2/api/plugins")
    if not resp:
        _has_groundstation = False
        return False

    # If the endpoint returned plain text, do a simple substring check
    if isinstance(resp, str):
        text = resp.lower()
        _has_groundstation = any(k in text for k in ("ground", "station", "notification"))
        return _has_groundstation

    # Recursively search JSON for plugin-like names
    def search(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and any(x in v.lower() for x in ("ground", "station", "notification")):
                    return True
                if search(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if search(item):
                    return True
        elif isinstance(obj, str):
            if any(x in obj.lower() for x in ("ground", "station", "notification")):
                return True
        return False

    _has_groundstation = search(resp)
    return _has_groundstation


def test_nina_connection():
    """Test basic NINA API connectivity."""
    print(f"[{get_timestamp()}] Testing NINA API connection...")
    print(f"[{get_timestamp()}] API URL: {NINA_API_URL}")

    status_data = query_nina_api(NINA_API_ENDPOINT_STATUS)
    if not status_data:
        print(f"[{get_timestamp()}] ? NINA API not reachable.")
        return False

    # Ensure we have a JSON/dict response before attempting to access keys
    # DEBUG: show the type and a short repr when unexpected
    if not isinstance(status_data, dict):
        print(f"[{get_timestamp()}] Debug: status_data type={type(status_data)!r}")
        try:
            preview = repr(status_data)[:200]
        except Exception:
            preview = "<unprintable>"
        print(f"[{get_timestamp()}] Debug: status_data repr (short): {preview}")
        print(f"[{get_timestamp()}] ? NINA API returned non-JSON response; treating as unreachable")
        return False

    resp_field = status_data.get("Response", {})
    if isinstance(resp_field, dict):
        version = resp_field.get("Version", "Unknown")
    else:
        # Unexpected shape: Response is not a dict
        print(f"[{get_timestamp()}] Warning: unexpected 'Response' field type: {type(resp_field)!r}")
        version = "Unknown"
    print(f"[{get_timestamp()}] ? NINA API connected successfully!")
    print(f"[{get_timestamp()}]  NINA Version: {version}")
    return True


def test_equipment_status():
    """Test reading equipment status (safe read-only operations)."""
    print(f"[{get_timestamp()}] Testing equipment status...")

    equipment_tests = [
        ("Camera", NINA_API_ENDPOINT_CAMERA),
        ("Mount", NINA_API_ENDPOINT_MOUNT),
        ("Dome", NINA_API_ENDPOINT_DOME),
    ]

    for equipment_name, endpoint in equipment_tests:
        data = query_nina_api(endpoint)
        if data:
            response_data = data.get("Response", {})
            connected = response_data.get("Connected", False)
            device_name = response_data.get("Name", "Unknown")
            status = "Connected" if connected else "Disconnected"
            print(f"[{get_timestamp()}]    {equipment_name}: {status} ({device_name})")
        else:
            print(f"[{get_timestamp()}]    {equipment_name}: Error accessing API")


def send_test_notification(message, title="obsybox NINA Test"):
    """Send test notification via Ground Station plugin (if available).

    Returns True if notification appears to have been accepted by NINA.
   """
    print(f"[{get_timestamp()}] Sending test notification: {title}")

    # Check whether the Ground Station / notification plugin is available
    if not check_groundstation_plugin():
        print(f"[{get_timestamp()}] Skipping notification: no ground-station/notification plugin detected")
        return False

    try:
        notification_data = {
            "Title": title,
            "Message": message,
            "Priority": 0,
            "Sound": "pushover",
        }

        url = f"{NINA_API_URL}/v2/api/plugins/groundstation/notification"
        response = requests.post(url, json=notification_data, timeout=5)

        if response.status_code == 200:
            print(f"[{get_timestamp()}] ? Notification sent successfully!")
            print(f"[{get_timestamp()}]    Message: {message}")
            return True
        else:
            print(f"[{get_timestamp()}] ?? Notification failed (status {response.status_code})")
            print(f"[{get_timestamp()}]    This is normal if Ground Station plugin not configured or endpoint differs")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[{get_timestamp()}] ?? Notification error: {e}")
        print(f"[{get_timestamp()}]    This is normal if Ground Station plugin not available")
        return False


def simulate_target_scheduler():
    """Simulate the target scheduler workflow with notifications.

    This function only sends notifications and logs as a safe way to
    emulate scheduling when running against simulator devices.
    """
    print(f"[{get_timestamp()}] Starting target scheduler simulation...")

    # Test targets
    test_targets = [
        {"name": "M42 Orion Nebula", "ra": "05:35:17", "dec": "-05:23:14"},
        {"name": "M31 Andromeda Galaxy", "ra": "00:42:44", "dec": "+41:16:09"},
        {"name": "M13 Hercules Cluster", "ra": "16:41:41", "dec": "+36:27:37"},
    ]

    # Send start notification
    send_test_notification(
        f"obsybox scheduler test started - {len(test_targets)} targets queued",
        "Scheduler Test Started",
    )

    # Simulate each target
    for i, target in enumerate(test_targets, 1):
        target_name = target["name"]
        ra = target["ra"]
        dec = target["dec"]

        print(f"[{get_timestamp()}] Processing Target {i}: {target_name}")
        print(f"[{get_timestamp()}]    Coordinates: RA {ra}, Dec {dec}")

        # Send target notification
        message = f"Target {i}/{len(test_targets)}: {target_name} (RA: {ra}, Dec: {dec})"
        send_test_notification(message, f"Target {i} Scheduled")

        # Wait 10 seconds between targets (simulated delay)
        print(f"[{get_timestamp()}]    Waiting 10 seconds before next target...")
        time.sleep(10)

        # Send completion notification
        send_test_notification(f"Target {i} simulation complete - {target_name}", f"Target {i} Complete")

    # Send final notification
    send_test_notification(
        f"Scheduler test completed - all {len(test_targets)} targets processed",
        "Test Complete",
    )

    print(f"[{get_timestamp()}] ? Target scheduler simulation complete!")


def main():
    """Main test function."""
    print("=" * 60)
    print("obsybox NINA API Test Suite")
    print("Safe testing mode - no hardware movement")
    print("=" * 60)
    print(f"[{get_timestamp()}] Starting test suite...")

    try:
        # Test 1: API Connection
        if not test_nina_connection():
            print(f"[{get_timestamp()}] ? Test failed - cannot connect to NINA API")
            print(f"[{get_timestamp()}] Make sure NINA is running and API is enabled")
            return False

        # Test 2: Equipment Status (read-only)
        test_equipment_status()

        # Test 3: Notification System
        print(f"[{get_timestamp()}] Testing notification system...")
        send_test_notification("NINA API test notification", "API Test")

        # Test 4: Scheduler Simulation
        print(f"[{get_timestamp()}] Starting scheduler simulation...")
        simulate_target_scheduler()

        print(f"[{get_timestamp()}] All tests completed successfully!")
        print(f"[{get_timestamp()}] Check your Ground Station / Pushover notifications for test messages")
        return True

    except KeyboardInterrupt:
        print(f"\n[{get_timestamp()}] Test interrupted by user")
        send_test_notification("NINA API test interrupted by user", "Test Stopped")
        return False
    except Exception as e:
        print(f"[{get_timestamp()}] Test failed with error: {e}")
        traceback.print_exc()
        send_test_notification(f"NINA API test failed: {str(e)}", "Test Error")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n[{get_timestamp()}] NINA API integration test PASSED!")
        print(f"[{get_timestamp()}] Ready for full scheduler integration")
    else:
        print(f"\n[{get_timestamp()}] NINA API integration test FAILED!")
        print(f"[{get_timestamp()}] Check NINA configuration before proceeding")
    sys.exit(0 if success else 1)