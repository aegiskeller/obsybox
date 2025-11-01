# NINA Scheduler API Test

Safe test suite for NINA API integration with obsybox scheduler. Tests target scheduling workflow using notifications only - **no hardware movement**.

## What This Test Does

? **Safe Operations Only:**
- Tests NINA API connectivity
- Reads equipment status (read-only)
- Sends Pushover notifications via Ground Station plugin
- Simulates target scheduling workflow
- No telescope movement, no camera commands

## Prerequisites

1. **NINA Running** with API enabled
   - Go to NINA Options ? API
   - Enable "Enable Web API"  
   - Default port: 1888

2. **Ground Station Plugin** (recommended)
   - For Pushover notifications
   - Not required - test will work without it

3. **Python** with requests module
   ```bash
   pip install requests
   ```

## Quick Start

### Windows (Batch File)
```cmd
run_nina_test.bat
```

### Windows (PowerShell)
```powershell
.\run_nina_scheduler_test.ps1
```

### Cross-Platform (Python)
```bash
python test_nina_scheduler_api.py
```

## Test Sequence

1. **Connection Test** - Verify NINA API is accessible
2. **Equipment Status** - Read current equipment connections (safe)
3. **Target Simulation** - Process 4 test targets:
   - M42 Orion Nebula
   - M31 Andromeda Galaxy  
   - M13 Hercules Cluster
   - NGC 7000 North America Nebula
4. **Notifications** - Send Pushover notifications for each target
5. **Completion** - Final summary notification

## Configuration

Edit `test_config.json` to customize:

```json
{
  "nina_api": {
    "base_url": "http://localhost:1888",
    "timeout_seconds": 10
  },
  "test_config": {
    "target_delay_seconds": 15,
    "enable_pushover": true
  },
  "test_targets": [
    {
      "name": "Custom Target",
    "ra": "12:34:56",
      "dec": "+12:34:56",
      "magnitude": 10.0,
  "exposure_time": 300
    }
  ]
}
```

## Safety Features

- **Read-Only API Calls** - Only queries equipment status
- **No Hardware Commands** - Never sends movement or control commands
- **Notification-Based** - Uses messaging to simulate scheduler actions
- **Keyboard Interrupt** - Can be safely stopped with Ctrl+C

## Expected Output

```
?? NINA Scheduler API Test
==================================================
Time: 2025-10-30 14:30:00
API Endpoint: http://localhost:1888/v2/api

? NINA API connected successfully
   NINA Version: 3.1.2.9001

?? Equipment Status Check:
   Camera: ? Connected (ZWO ASI183MC Pro)
   Mount: ? Connected (iOptron CEM25P)
   Focuser: ? Disconnected (N/A)
 Filterwheel: ? Disconnected (N/A)
   Dome: ? Connected (RRCI Rolling Roof)

?? Starting Target Scheduling Simulation
   Testing 4 targets with 15-second intervals

? Notification sent: obsybox scheduler test started - 4 targets queued
? Notification sent: Connected equipment: camera, mount, dome
   ?? Target 1: M42 Orion Nebula
      Coordinates: RA 05:35:17, Dec -05:23:14
      ??  Waiting 15 seconds before next target...
? Notification sent: Target 1/4: M42 Orion Nebula (RA: 05:35:17, Dec: -05:23:14)
...

? Target scheduling simulation complete!
?? All tests completed successfully!
   Check your Pushover notifications for test messages
```

## Troubleshooting

### "Cannot connect to NINA API"
- Ensure NINA is running
- Check NINA Options ? API ? Enable Web API
- Verify port 1888 is not blocked by firewall
- Try accessing http://localhost:1888/v2/api/version in browser

### "Notification failed"
- Ground Station plugin may not be installed
- Pushover settings may not be configured
- Test will still work, just won't send external notifications

### "Equipment shows disconnected"
- This is normal if equipment isn't connected
- Test focuses on API functionality, not hardware status

## Integration with obsybox

This test validates the API integration approach for your automated scheduler:

1. **Target Generation** - Your existing `findTargets.py` 
2. **API Communication** - This test validates NINA API access
3. **Equipment Monitoring** - Reads current equipment status
4. **Notification System** - Tests alert/notification workflow
5. **Scheduler Logic** - Simulates target switching workflow

## Next Steps

After successful testing:
1. Integrate API calls into your existing `findTargets.py`
2. Add real-time equipment monitoring
3. Implement automatic sequence switching
4. Add weather-based pause/resume logic
5. Create complete automated observation workflow

## Files

- `test_nina_scheduler_api.py` - Main test script  
- `test_config.json` - Configuration file
- `run_nina_test.bat` - Windows batch launcher
- `run_nina_scheduler_test.ps1` - PowerShell launcher
- `README.md` - This documentation