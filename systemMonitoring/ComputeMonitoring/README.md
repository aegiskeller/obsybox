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

### Quick Deploy (Recommended for Piglet)

The easiest way to deploy on Piglet is using the automated deployment script:

```powershell
# Run PowerShell as Administrator
cd C:\Users\aegis\Documents\obsybox

# Deploy the task (auto-detects Python)
.\systemMonitoring\ComputeMonitoring\deploy_task.ps1 -Force

# Monitor the logs
Get-Content C:\Logs\obsybox\get_system_stats.log -Tail 10 -Wait
```

The deployment script will:
- ✅ Auto-detect Python installation path
- ✅ Create wrapper script with correct paths
- ✅ Register scheduled task to run every minute
- ✅ Run under your user account (PIGLET\aegis)
- ✅ Create log directory and files
- ✅ Test the task immediately

### Piglet-Specific Configuration

**Machine**: `PIGLET\aegis`
**Python Path**: `C:\Users\aegis\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe`
**Script Path**: `C:\Users\aegis\Documents\obsybox\systemMonitoring\ComputeMonitoring\get_system_stats.py`
**Log File**: `C:\Logs\obsybox\get_system_stats.log`
**Task Name**: `Obsybox_GetSystemStats`
**Monitored Drive**: `C:`
**Run Interval**: Every 60 seconds

### Undeploy Task

To remove the scheduled task:

```powershell
# Run PowerShell as Administrator
cd C:\Users\aegis\Documents\obsybox

# Remove task only
.\systemMonitoring\ComputeMonitoring\undeploy_task.ps1

# Remove task and log file
.\systemMonitoring\ComputeMonitoring\undeploy_task.ps1 -RemoveLog
```

### Manual Task Scheduler Setup (Alternative)

If you prefer to configure manually instead of using the deployment script:

#### 1. Open Task Scheduler
#### 1. Open Task Scheduler
- Press Windows Key
- Type "Task Scheduler"
- Open Task Scheduler

#### 2. Create New Task
- Click "Create Task..." (not "Create Basic Task")

#### 3. General Tab
- **Name**: `Obsybox_GetSystemStats`
- **Security options**:
  - ☑ Run whether user is logged on or not
  - ☐ Do not store password (unchecked)
  - ☑ Run with highest privileges
- **Configure for**: Windows 10 or Windows 11

#### 4. Triggers Tab
- Click "New..."
- **Begin the task**: On a schedule
- **Settings**: Daily, recur every 1 day
- **Repeat task every**: 1 minute
- **For a duration of**: Indefinitely
- Click OK

#### 5. Actions Tab
- Click "New..."
- **Action**: Start a program
- **Program/script**: `C:\Users\aegis\Documents\obsybox\systemMonitoring\ComputeMonitoring\run_get_system_stats.cmd`
- **Add arguments**: *(leave blank)*
- **Start in**: *(leave blank)*

**IMPORTANT for Piglet**: Use the wrapper script `run_get_system_stats.cmd` which contains the correct Python path.

#### 6. Settings Tab
- ☐ Stop the task if it runs longer than (unchecked - runs indefinitely)
- ☑ If the running task does not end when requested, force it to stop
- ☐ If the task is already running, do not start a new instance

#### 7. Save
- Click OK
- Enter your password if prompted

## Verifying the Task

### Check Task Status
```powershell
Get-ScheduledTask -TaskName "Obsybox_GetSystemStats" | Format-List
```

### View Last Run Result
```powershell
# Requires Administrator privileges
Get-ScheduledTaskInfo -TaskName "Obsybox_GetSystemStats"
```

### Run Task Manually
```powershell
# Requires Administrator privileges
Start-ScheduledTask -TaskName "Obsybox_GetSystemStats"
```

### Stop Running Task
```powershell
# Requires Administrator privileges
Stop-ScheduledTask -TaskName "Obsybox_GetSystemStats"
```

### Monitor Logs in Real-Time
```powershell
# Watch the log file (works for any user)
Get-Content C:\Logs\obsybox\get_system_stats.log -Tail 10 -Wait
```

## Troubleshooting

### Common Errors

**Error 2147942402** (0x80070005) - "The system cannot find the file specified"
- This means the Python path in the wrapper script is incorrect
- **Fix**: Run `.\systemMonitoring\ComputeMonitoring\deploy_task.ps1 -Force` to auto-detect and fix
- **Manual Fix**: Edit `run_get_system_stats.cmd` to use the correct Python path from `python -c "import sys; print(sys.executable)"`

**Error 2147942667** (0x8007010B) - "The directory name is invalid"
- Remove quotes from "Start in" field in Task Scheduler
- Verify the path exists

**Task runs but nothing published**
- Check if MQTT broker is accessible: `Test-NetConnection 192.168.1.49 -Port 1883`
- Verify `paho-mqtt` is installed: `python -m pip list | Select-String paho`
- Install if needed: `pip install paho-mqtt`
- Check log file for errors: `Get-Content C:\Logs\obsybox\get_system_stats.log -Tail 20`

**No CPU temperature**
- Install LibreHardwareMonitor and ensure it's running on port 8085
- Or install `psutil` for basic temperature support (Linux-style sensors)

**Wrapper script shows "The system cannot execute the specified program"**
- This is the old error before the fix - Python path was wrong
- Should be resolved after running deploy script

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
