#!/usr/bin/env python3
"""
Safe test case for NINA API integration - Scheduler simulation
Tests target scheduling workflow using notifications only (no hardware movement)
"""
import requests
import json
import time
from datetime import datetime
from pathlib import Path
import sys

# NINA API Configuration
NINA_API_BASE = "http://localhost:1888"  # Default NINA API endpoint
NINA_API_VERSION = "v2"

class NINASchedulerTest:
    def __init__(self, api_base=NINA_API_BASE):
 self.api_base = api_base
        self.api_url = f"{api_base}/{NINA_API_VERSION}/api"
        self.session = requests.Session()
        self.session.timeout = 10
        
    def test_connection(self):
        """Test if NINA API is accessible"""
      try:
    response = self.session.get(f"{self.api_url}/version")
      if response.status_code == 200:
                version_info = response.json()
     print(f"? NINA API connected successfully")
       print(f"   NINA Version: {version_info.get('Response', {}).get('Version', 'Unknown')}")
              return True
            else:
      print(f"? NINA API returned status {response.status_code}")
                return False
    except requests.exceptions.RequestException as e:
          print(f"? Failed to connect to NINA API: {e}")
       print(f"   Make sure NINA is running and API is enabled on {self.api_base}")
return False
    
    def send_ground_station_notification(self, message, title="obsybox Scheduler Test"):
  """
    Send notification via Ground Station plugin
        This safely tests the notification system without hardware movement
        """
  try:
     # Ground Station notification endpoint
     notification_data = {
                "Title": title,
 "Message": message,
             "Priority": 0,  # Normal priority
"Sound": "pushover"
        }
            
            response = self.session.post(
     f"{self.api_url}/plugins/groundstation/notification",
                json=notification_data
            )
    
            if response.status_code == 200:
 print(f"? Notification sent: {message}")
 return True
          else:
print(f"??  Notification failed (status {response.status_code}): {message}")
          # Try alternative notification method
           return self._try_alternative_notification(message, title)
       
        except requests.exceptions.RequestException as e:
     print(f"?? Notification error: {e}")
            return self._try_alternative_notification(message, title)
    
    def _try_alternative_notification(self, message, title):
        """Try alternative notification methods if Ground Station fails"""
      try:
 # Try generic notification endpoint
        notification_data = {
          "message": message,
       "title": title
            }
    
            response = self.session.post(
  f"{self.api_url}/notification",
                json=notification_data
     )
      
            if response.status_code == 200:
            print(f"? Alt notification sent: {message}")
                return True
            else:
         print(f"? All notification methods failed for: {message}")
          return False
  
        except Exception as e:
 print(f"? Alternative notification failed: {e}")
            return False
    
    def get_equipment_status(self):
   """Get current equipment status (safe read-only operation)"""
        equipment_status = {}
        
        endpoints = {
       "camera": "/equipment/camera/info",
 "mount": "/equipment/mount/info", 
     "focuser": "/equipment/focuser/info",
            "filterwheel": "/equipment/filterwheel/info",
       "dome": "/equipment/dome/info"
        }
        
        for equipment, endpoint in endpoints.items():
          try:
          response = self.session.get(f"{self.api_url}{endpoint}")
     if response.status_code == 200:
                  data = response.json().get('Response', {})
  equipment_status[equipment] = {
    'connected': data.get('Connected', False),
            'name': data.get('Name', 'Unknown')
         }
     else:
                equipment_status[equipment] = {'connected': False, 'name': 'N/A'}
            except:
             equipment_status[equipment] = {'connected': False, 'name': 'Error'}
        
        return equipment_status
    
    def simulate_target_schedule(self, targets):
        """
   Simulate target scheduling workflow using notifications
        This is completely safe - no hardware commands sent
        """
        print(f"\n?? Starting Target Scheduling Simulation")
        print(f"   Testing {len(targets)} targets with 15-second intervals")
        
        # Send initial notification
  self.send_ground_station_notification(
       f"obsybox scheduler test started - {len(targets)} targets queued",
        "Scheduler Test Started"
        )
        
# Get equipment status for context
        equipment = self.get_equipment_status()
        connected_equipment = [name for name, info in equipment.items() if info['connected']]
        
        if connected_equipment:
      self.send_ground_station_notification(
         f"Connected equipment: {', '.join(connected_equipment)}",
      "Equipment Status"
       )
        
        # Simulate each target
    for i, target in enumerate(targets, 1):
       target_name = target.get('name', f'Target {i}')
         ra = target.get('ra', '00:00:00')
            dec = target.get('dec', '+00:00:00')
        
       # Send target notification
      message = f"Target {i}/{len(targets)}: {target_name} (RA: {ra}, Dec: {dec})"
            self.send_ground_station_notification(message, f"Target {i} Scheduled")
            
    # Simulate some scheduler activity
          print(f"   ?? Target {i}: {target_name}")
            print(f"      Coordinates: RA {ra}, Dec {dec}")
            print(f"      ??  Waiting 15 seconds before next target...")
      
# Wait 15 seconds (simulating observation time)
      time.sleep(15)
         
            # Send completion notification for this target
         self.send_ground_station_notification(
        f"Target {i} simulation complete - {target_name}",
           f"Target {i} Complete"
            )
   
  # Send final completion notification
        self.send_ground_station_notification(
    f"Scheduler test completed - all {len(targets)} targets processed",
    "Test Complete ?"
        )
        
        print(f"\n? Target scheduling simulation complete!")
    
    def run_scheduler_test(self):
        """Main test function"""
        print(f"?? NINA Scheduler API Test")
        print(f"=" * 50)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
   print(f"API Endpoint: {self.api_url}")

        # Test 1: Connection
   if not self.test_connection():
       print(f"\n? Test failed: Cannot connect to NINA API")
            return False
        
        # Test 2: Equipment status
        print(f"\n?? Equipment Status Check:")
        equipment = self.get_equipment_status()
        for name, info in equipment.items():
            status = "? Connected" if info['connected'] else "? Disconnected"
    print(f"   {name.capitalize()}: {status} ({info['name']})")
  
        # Test 3: Create test targets
        test_targets = [
            {
              'name': 'M42 Orion Nebula',
       'ra': '05:35:17',
     'dec': '-05:23:14',
                'mag': 4.0,
                'type': 'Nebula'
            },
    {
    'name': 'M31 Andromeda Galaxy', 
  'ra': '00:42:44',
     'dec': '+41:16:09',
      'mag': 3.4,
            'type': 'Galaxy'
        },
            {
      'name': 'M13 Hercules Cluster',
          'ra': '16:41:41',
   'dec': '+36:27:37',
           'mag': 5.8,
     'type': 'Globular Cluster'
     }
        ]
        
        # Test 4: Simulate scheduling
        try:
            self.simulate_target_schedule(test_targets)
 return True
        except KeyboardInterrupt:
            print(f"\n??  Test interrupted by user")
      self.send_ground_station_notification(
 "Scheduler test interrupted by user",
        "Test Stopped"
)
      return False
      except Exception as e:
  print(f"\n? Test failed with error: {e}")
    self.send_ground_station_notification(
     f"Scheduler test failed: {str(e)}",
        "Test Error"
     )
      return False

def main():
    """Main entry point"""
    print(f"obsybox NINA Scheduler Test")
  print(f"Safe testing mode - no hardware movement")
    print(f"Uses notifications only via Ground Station plugin")
    
    # Check if custom API endpoint provided
    api_endpoint = NINA_API_BASE
    if len(sys.argv) > 1:
        api_endpoint = sys.argv[1]
        print(f"Using custom API endpoint: {api_endpoint}")
    
    # Create and run test
    tester = NINASchedulerTest(api_endpoint)
    
    try:
        success = tester.run_scheduler_test()
        if success:
  print(f"\n?? All tests completed successfully!")
          print(f"   Check your Pushover notifications for test messages")
        else:
     print(f"\n? Some tests failed - check NINA configuration")
         return 1
     
    except KeyboardInterrupt:
        print(f"\n?? Test cancelled by user")
        return 0
    except Exception as e:
    print(f"\n?? Test crashed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())