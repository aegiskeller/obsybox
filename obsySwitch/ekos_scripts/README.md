# Ekos External Scripts for ObsyBox Switch

Simple shell scripts to control your relay switches from Ekos Scheduler.

**Perfect for macOS** where INDI Alpaca driver may not be available!

---

## Setup

### 1. Make Scripts Executable

```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/ekos_scripts
chmod +x *.sh
```

### 2. Test Scripts

Make sure Alpaca server is running first:
```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch
python ascom_switch_server.py
```

Then test each script:
```bash
# Check current status
./check_status.sh

# Test power on
./power_on.sh

# Test power off
./power_off.sh
```

---

## Using in Ekos Scheduler

### Startup Procedure

1. Open **Ekos Scheduler**
2. Select or create a job
3. In **Startup Procedure** section:
   - Check **Execute Script**
   - Browse to: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/ekos_scripts/power_on.sh`

### Shutdown Procedure

1. In **Shutdown Procedure** section:
   - Check **Execute Script**
   - Browse to: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/ekos_scripts/power_off.sh`

### Emergency Abort

1. In **Job Constraints** or **Abort** settings:
   - Set abort script to: `emergency_stop.sh`

---

## Individual Switch Control

Create custom scripts for specific equipment:

### Mount Only
```bash
#!/bin/bash
curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/0 \
  -H "Content-Type: application/json" \
  -d '{"State":true}'
```

### Camera Only
```bash
#!/bin/bash
curl -X PUT http://localhost:8080/api/v1/switch/0/setswitch/1 \
  -H "Content-Type: application/json" \
  -d '{"State":false}'
```

---

## Advanced: Python Integration

For more complex logic, create Python scripts:

**ekos_smart_power.py:**
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from obsyswitch_serial_driver import ObsySwitchSerialController

def power_sequence(action):
    controller = ObsySwitchSerialController()
    controller.connect()
    
    if action == "startup":
        # Intelligent startup with delays
        controller.set_switch(0, True)  # Mount
        time.sleep(5)  # Wait for mount to stabilize
        controller.set_switch(1, True)  # Camera
        controller.set_switch(2, True)  # Focuser
        
    elif action == "shutdown":
        # Safe shutdown order
        controller.set_switch(1, False)  # Camera first
        time.sleep(2)  # Let camera cool down
        controller.set_switch(2, False)  # Focuser
        controller.set_switch(0, False)  # Mount last
    
    controller.disconnect()

if __name__ == "__main__":
    power_sequence(sys.argv[1])
```

Use in Ekos:
```bash
python ekos_smart_power.py startup
python ekos_smart_power.py shutdown
```

---

## Troubleshooting

### Script Hangs or Times Out

Check if Alpaca server is running:
```bash
curl http://localhost:8080/status
```

### Permission Denied

Make scripts executable:
```bash
chmod +x /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/ekos_scripts/*.sh
```

### Scripts Don't Run from Ekos

Check Ekos logs:
- Go to KStars → Tools → Logs
- Look for script execution errors

Ensure full paths are used in Ekos configuration.

---

## Status Monitoring

Add status check to **Pre-Job** scripts:

```bash
#!/bin/bash
# Pre-flight check
if ! curl -s http://localhost:8080/status > /dev/null 2>&1; then
    echo "ERROR: Switch controller not available!"
    exit 1
fi

# Continue with power-on...
./power_on.sh
```

---

## Integration Tips

1. **Always start Alpaca server first** before running Ekos
2. **Test scripts manually** before using in scheduler
3. **Add delays** between switch operations for equipment safety
4. **Monitor logs** at `/status` endpoint for debugging
5. **Use emergency_stop.sh** for safety procedures

---

## Comparison: Scripts vs INDI Driver

| Feature | External Scripts | INDI Driver |
|---------|-----------------|-------------|
| macOS Support | ✅ Excellent | ⚠️ Limited |
| Setup Complexity | 🟢 Simple | 🔴 Complex |
| Ekos Integration | 🟡 Manual | 🟢 Native |
| Flexibility | 🟢 Full control | 🟡 Standard only |
| Debugging | 🟢 Easy | 🔴 Difficult |

**Recommendation for macOS:** Use external scripts until INDI Alpaca is officially supported.
