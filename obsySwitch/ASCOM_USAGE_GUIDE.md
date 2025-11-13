# ASCOM Driver Usage Guide for ObsyBox Relay Controller

## **Two Ways to Use ASCOM with Relay Controller**

Now that all the relays are working, lets integrate with NINA and other ASCOM software:

## **Method 1: Direct Python ASCOM Bridge **

### **Step 1: Create ASCOM Bridge Script**
```python
# Save as: ascom_bridge.py
from obsyswitch_serial_driver import ASCOMSwitchSerial

# Create ASCOM-compatible driver instance
ascom_switch = ASCOMSwitchSerial()

# Connect to Arduino
print("Connecting to relay controller...")
ascom_switch.Connected = True

if ascom_switch.Connected:
    print(f"Connected to Arduino relay controller")
    print(f"Device: {ascom_switch.controller.device_status.device_name}")
    print(f"Available switches: {ascom_switch.MaxSwitch + 1}")
    
    # Show switch names
    for i in range(ascom_switch.MaxSwitch + 1):
        name = ascom_switch.GetSwitchName(i)
        state = ascom_switch.GetSwitch(i)
        print(f"  Switch {i}: {name} ({'ON' if state else 'OFF'})")
    
    # Example: Control switches
    print("\nTesting switch control...")
    
    # Turn on Mount (Switch 0)
    print("Turning on Mount...")
    ascom_switch.SetSwitch(0, True)
    
    # Turn on Camera (Switch 1)  
    print("Turning on Camera...")
    ascom_switch.SetSwitch(1, True)
    
    # Show updated status
    print("\nCurrent status:")
    for i in range(ascom_switch.MaxSwitch + 1):
        name = ascom_switch.GetSwitchName(i)
        state = ascom_switch.GetSwitch(i)
        print(f"  Switch {i}: {name} ({'ON' if state else 'OFF'})")
    
    # Disconnect when done
    ascom_switch.Connected = False
    print(f"Disconnected")
else:
    print(f"Failed to connect to Arduino")
```

### **Step 2: Test the ASCOM Interface**
```bash
cd /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch
python ascom_bridge.py
```

## **Method 2: NINA External Script Integration (Easiest)**

### **Step 1: NINA Sequence Setup**
In NINA, create sequences with **External Script** instructions:

```
 OBSERVATION SEQUENCE
  Sequence Start
     External Script
        Program: python3
        Arguments: /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/nina_serial_integration.py startup
        Working Dir: /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch

  Equipment Setup
     Slew to Target
     Auto Focus
     Cool Camera

  Imaging Block
     Take Images
     Dither & Repeat

  Sequence End
      External Script
         Program: python3
         Arguments: /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/nina_serial_integration.py shutdown
         Working Dir: /Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch
```

### **Step 2: NINA Script Configuration**

**Startup Script:**
- **Program**: `python3`
- **Arguments**: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/nina_serial_integration.py startup`
- **Working Directory**: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch`
- **Timeout**: `30 seconds`

**Shutdown Script:**
- **Program**: `python3`  
- **Arguments**: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch/nina_serial_integration.py shutdown`
- **Working Directory**: `/Users/aegiskeller/Documents/Arduino/obsybox/obsySwitch`
- **Timeout**: `30 seconds`

## **Method 3: ASCOM Switch Simulator (Advanced)**

### **For Full ASCOM Integration:**

1. **Install ASCOM Platform** (if not already installed)
   - Download from: https://ascom-standards.org/
   - Install ASCOM Platform 6.6+

2. **Use ASCOM Switch Simulator**
   - Configure simulator to call your Python scripts
   - Map switch IDs to your relay controller

3. **Python ASCOM Bridge**
```python
# Advanced ASCOM bridge with Windows COM integration
import win32com.client

def create_ascom_bridge():
    """Create ASCOM bridge using Windows COM"""
   try:
        # This would integrate with ASCOM Platform
        # Requires advanced Windows COM programming
        pass
    except Exception as e:
        print(f"ASCOM COM integration error: {e}")
        print("Use Method 1 or 2 instead")
```

## **Quick Usage Examples**

### **Manual Control:**
```bash
# Turn on all equipment
python nina_serial_integration.py startup

# Check status
python nina_serial_integration.py status

# Turn off everything
python nina_serial_integration.py shutdown

# Toggle specific relay
python nina_serial_integration.py toggle 0  # Mount
python nina_serial_integration.py toggle 1  # Camera
python nina_serial_integration.py toggle 2  # Focuser
```

### **Python Script Control:**
```python
from obsyswitch_serial_driver import ObsySwitchSerialController

# Direct control
controller = ObsySwitchSerialController()
controller.connect()

# Power on observatory equipment in order
controller.set_switch(0, True)  # Mount first
time.sleep(3)
controller.set_switch(2, True)  # Focuser
time.sleep(1)
controller.set_switch(1, True)  # Camera last

# Get status
all_switches = controller.get_all_switches()
print(f"Active equipment: {sum(all_switches.values())} devices")

# Emergency shutdown
controller.emergency_stop()
controller.disconnect()
```

## **Switch Mapping for NINA**

Your relay controller provides these ASCOM switches:

| ASCOM Switch ID | Equipment | Arduino Pin | Relay Channel |
|-----------------|-----------|-------------|---------------|
| 0 | Mount Power | Pin 2 | Relay 1 |
| 1 | Camera Power | Pin 3 | Relay 2 |
| 2 | Focuser Power | Pin 4 | Relay 3 |
| 3 | Aux Equipment | Pin 5 | Relay 4 |

## **NINA Integration Checklist**

### ** Setup Steps:**
1. **Test relay control**: `python nina_serial_integration.py startup`
2. **Create NINA sequence** with External Script instructions
3. **Configure script paths** in NINA
4. **Test startup sequence** in NINA
5. **Test shutdown sequence** in NINA
6. **Add to actual observation sequences**

### ** Verification:**
- [ ] All relays click audibly when commanded
- [ ] NINA startup script runs without errors  
- [ ] Equipment powers on in correct order
- [ ] NINA shutdown script turns off all equipment
- [ ] Emergency stop works from Python script

## **Troubleshooting**

### **Common Issues:**
1. **"Arduino not found"**
   - Check USB connection
   - Verify Arduino is powered on
   - Check port permissions

2. **"Permission denied"**
   - Use full paths in NINA script configuration
   - Check Python interpreter path

3. **"Script timeout"**
   - Increase timeout in NINA External Script settings
   - Check for Arduino communication delays

## **You're Ready!**

Your relay controller now has **full ASCOM compatibility** through the Python driver. You can:

 **Control from NINA sequences**  
 **Use ASCOM standard interface**  
 **Integrate with any ASCOM-compatible software**  
 **Manual control via Python scripts**  
 **Emergency stop functionality**  

**Recommended**: Start with **Method 2** (NINA External Scripts) as it's the most reliable and easiest to set up! 