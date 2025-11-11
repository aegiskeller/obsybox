# System Monitoring MQTT Publisher

Continuous system health monitoring that publishes metrics to MQTT broker every 60 seconds.

## Overview

The `get_system_stats.py` script collects and publishes system metrics to the MQTT broker at `192.168.1.49` on topic `obsybox/system_monitoring`.

### Metrics Published

- `hostname` - Computer name
- `cpu_temp_c` - CPU temperature in Celsius (if available)
- `cpu_load` - CPU load percentage (0-100)
- `disk_free_gb` - Free disk space in GB
- `wifi_signal_percent` - Wi-Fi signal strength percentage
- `wifi_signal_dbm` - Wi-Fi signal strength in dBm

Null values are automatically omitted from published JSON.

## Running the Script

The script runs in a continuous loop, publishing every 60 seconds until stopped.

### Manual Run
```powershell
cd C:\Users\Admin\Documents\Arduino\obsybox\systemMonitoring\ComputeMonitoring
python get_system_stats.py
```

Press Ctrl+C to stop.

### Optional: Override Drive to Monitor
```powershell
python get_system_stats.py E:
```

## Task Scheduler Setup

To run automatically at startup:

### 1. Open Task Scheduler
- Press Windows Key
- Type "Task Scheduler"
- Open Task Scheduler

### 2. Create New Task
- Click "Create Task..." (not "Create Basic Task")

### 3. General Tab
- **Name**: `Obsybox_Compute_monitor`
- **Security options**:
  - ☑ Run whether user is logged on or not
  - ☐ Do not store password (unchecked)
  - ☑ Run with highest privileges (optional, needed for some WMI queries)
- **Configure for**: Windows 10 or Windows 11

### 4. Triggers Tab
- Click "New..."
- **Begin the task**: At startup (or "At log on" if preferred)
- Click OK

### 5. Actions Tab
- Click "New..."
- **Action**: Start a program
- **Program/script**: `C:\Python310\python.exe`
- **Add arguments (optional)**: `"C:\Users\Admin\Documents\Arduino\obsybox\systemMonitoring\ComputeMonitoring\get_system_stats.py"`
- **Start in (optional)**: `C:\Users\Admin\Documents\Arduino\obsybox\systemMonitoring\ComputeMonitoring`

**IMPORTANT**: 
- Arguments field **WITH** quotes
- Start in field **WITHOUT** quotes

### 6. Settings Tab (Optional)
- ☐ Stop the task if it runs longer than (unchecked - runs indefinitely)
- ☑ If the running task does not end when requested, force it to stop
- ☐ If the task is already running, do not start a new instance

### 7. Save
- Click OK
- Enter your password if prompted

## Verifying the Task

### Check Task Status
```powershell
Get-ScheduledTask -TaskName "Obsybox_Compute_monitor" | Format-List
```

### View Last Run Result
```powershell
Get-ScheduledTaskInfo -TaskName "Obsybox_Compute_monitor"
```

### Run Task Manually
```powershell
Start-ScheduledTask -TaskName "Obsybox_Compute_monitor"
```

### Stop Running Task
```powershell
Stop-ScheduledTask -TaskName "Obsybox_Compute_monitor"
```

## Troubleshooting

### Common Errors

**Error 2147942667** (0x8007010B) - "The directory name is invalid"
- Remove quotes from "Start in" field in Task Scheduler
- Verify the path exists

**Task runs but nothing published**
- Check if MQTT broker is accessible: `Test-NetConnection 192.168.1.49 -Port 1883`
- Verify `paho-mqtt` is installed: `python -m pip list | Select-String paho`
- Install if needed: `pip install paho-mqtt`

**No CPU temperature**
- Install LibreHardwareMonitor and ensure it's running on port 8085
- Or install `psutil` for basic temperature support (Linux-style sensors)

### Dependencies

Optional Python packages for enhanced functionality:
```powershell
pip install paho-mqtt psutil requests
```

- `paho-mqtt` - Preferred MQTT publishing method
- `psutil` - Enhanced system metrics (CPU load, disk usage, temperatures)
- `requests` - LibreHardwareMonitor integration for CPU temperature

If packages aren't available, the script falls back to:
- `mosquitto_pub` command for MQTT
- PowerShell WMI for CPU load
- `shutil.disk_usage()` for disk space
- `netsh wlan` for Wi-Fi signal

## Drive Monitoring Configuration

The script auto-detects which drive to monitor based on hostname:
- `piglet` → monitors C:
- All other machines → monitors D:

To add custom mappings, edit `get_system_stats.py`:
```python
drive_mappings = {
    'piglet': 'C:',
    'yourhostname': 'E:',  # Add your custom mapping
}
```

## MQTT Topic

Published to: `obsybox/system_monitoring`

Example payload:
```json
{"hostname":"desktop-2gcqrlm","cpu_load":23.4,"disk_free_gb":512.75,"wifi_signal_percent":78,"wifi_signal_dbm":-61}
```
