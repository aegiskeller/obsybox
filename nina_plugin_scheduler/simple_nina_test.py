#!/usr/bin/env python3
"""
Simple NINA API test - minimal version
"""
import requests
import time

def test_nina_api():
    """Test basic NINA API connectivity"""
    api_url = "http://localhost:1888/v2/api"
    
    print("?? Testing NINA API...")
    print(f"API URL: {api_url}")
    
    try:
        # Test connection
        response = requests.get(f"{api_url}/version", timeout=10)
        if response.status_code == 200:
            print("? NINA API connected successfully")
            version_info = response.json()
            print(f"   Version: {version_info.get('Response', {}).get('Version', 'Unknown')}")
        else:
            print(f"? API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"? Connection failed: {e}")
        return False
    
    # Test equipment status
    print("\n?? Equipment Status:")
    endpoints = {
        "camera": "/equipment/camera/info",
        "mount": "/equipment/mount/info",
        "dome": "/equipment/dome/info"
    }
    
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{api_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                data = response.json().get('Response', {})
                connected = data.get('Connected', False)
                device_name = data.get('Name', 'Unknown')
                status = "? Connected" if connected else "? Disconnected"
                print(f"   {name}: {status} ({device_name})")
            else:
                print(f"   {name}: ? Error (status {response.status_code})")
        except Exception as e:
            print(f"   {name}: ? Error ({e})")
    
    # Test notification (simple approach)
    print("\n?? Testing Notifications:")
    try:
        # Try simple notification
        notification_data = {
            "Title": "obsybox Test",
            "Message": "NINA API test successful!",
            "Priority": 0
        }
        
        response = requests.post(
            f"{api_url}/plugins/groundstation/notification",
            json=notification_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print("? Notification sent successfully")
        else:
            print(f"?? Notification failed (status {response.status_code})")
            print("   (This is normal if Ground Station plugin not configured)")
    except Exception as e:
        print(f"?? Notification error: {e}")
        print("   (This is normal if Ground Station plugin not available)")
    
    print("\n?? API test completed!")
    return True

if __name__ == "__main__":
    print("obsybox NINA API Simple Test")
    print("=" * 40)
    
    success = test_nina_api()
    if success:
        print("\n? Test passed - NINA API is working")
    else:
        print("\n? Test failed - check NINA is running and API enabled")
        exit(1)