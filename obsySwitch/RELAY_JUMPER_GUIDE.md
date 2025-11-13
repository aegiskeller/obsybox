# Relay Board Jumper Configuration Guide

## **Common Relay Board Jumpers**

Most 4-channel relay boards have several jumper configurations that affect how the relays operate. Here are the most common ones:

### **1. VCC Power Selection Jumpers**
**Location**: Usually near the power input pins  
**Purpose**: Select power source for relay coils

**Common Configurations**:
```
JD-VCC --- VCC  (Jumper connected)

 5V Input from Arduino

OR

JD-VCC     VCC  (Jumper removed)
          
External   Arduino 5V
5V Supply  (logic only)
```

**What this means**:
- **Jumper ON**: Relay coils powered by Arduino 5V (simpler setup)
- **Jumper OFF**: Relay coils need separate external 5V supply (isolated/safer)

### **2. Signal Level Jumpers**
**Location**: Near the input pins (IN1, IN2, IN3, IN4)  
**Purpose**: Set trigger voltage level

**Configurations**:
- **5V**: Relays trigger with 5V signals (Arduino Uno default)
- **3.3V**: Relays trigger with 3.3V signals (ESP32, Raspberry Pi)

### **3. Trigger Type Jumpers**
**Location**: Sometimes labeled as "HIGH/LOW" or "H/L"  
**Purpose**: Set active HIGH vs active LOW triggering

**Settings**:
- **Active LOW** (most common): Relay turns ON when signal goes LOW (0V)
- **Active HIGH**: Relay turns ON when signal goes HIGH (5V)

## **Diagnosing Your Board**

Since **Relay 4 isn't clicking** but the others work, let's check the jumpers:

### **Step 1: Visual Inspection**
Look for these jumper configurations on your relay board:

1. **Power jumpers** - Usually 2-3 pins with a small plastic cap
2. **Individual relay jumpers** - One set per relay channel
3. **Overall board configuration jumpers**

### **Step 2: Compare Working vs Non-Working Relays**
- Check if **Relay 4** has different jumper settings than **Relays 1-3**
- Look for missing jumper caps on **Relay 4's channel**

### **Step 3: Common Relay 4 Issues**
```
Possible Causes:
 Missing jumper cap on Relay 4 channel
 Different trigger level setting
 Power isolation jumper in wrong position
 Physical jumper pins bent/damaged
```

## **Troubleshooting Steps**

### **Option 1: Match Relay 4 to Working Relays**
1. **Compare jumpers**: Make sure **Relay 4** has identical jumper settings to **Relays 1-3**
2. **Check for missing caps**: Ensure all jumper caps are present
3. **Verify alignment**: Make sure jumper caps are fully seated

### **Option 2: Try Different Jumper Positions**
1. **Document current settings** (take a photo!)
2. **Try moving Relay 4 jumpers** to different positions
3. **Test after each change**:
   ```bash
   python test_all_relays.py
   ```

### **Option 3: Check Power Isolation**
If your board has **VCC/JD-VCC jumpers**:

**Current Setup (likely)**:
```
JD-VCC  VCC  (Jumper connected)
```

**Try Isolated Power**:
```
JD-VCC     VCC  (Jumper removed)
          
External   Arduino 5V
5V Supply  (signal only)
```

## **Common Relay Board Types**

### **Type 1: Simple Relay Board**
```
Jumpers:
- VCC selection (JD-VCC  VCC)
- Trigger level per channel (H/L)
```

### **Type 2: Optoisolated Relay Board**
```
Jumpers:
- Power isolation (VCC/JD-VCC)
- Signal voltage (5V/3.3V)
- Individual channel enable/disable
```

### **Type 3: Advanced Relay Board**
```
Jumpers:
- Multiple power options
- Individual relay configuration
- Pull-up/Pull-down resistors
- LED indicator enable/disable
```

## **Quick Diagnostic Commands**

### **Test Individual Relay 4**
```bash
# Test just Relay 4 repeatedly
python -c "
import serial
import time
ser = serial.Serial('/dev/cu.usbserial-14120', 9600)
time.sleep(2)
for i in range(5):
    ser.write(b'SET_RELAY,4,TOGGLE\\n')
    time.sleep(1)
    print(f'Toggle {i+1} - Listen for click!')
ser.close()
"
```

### **Check Relay 4 LED Indicator**
When running the above command:
-  **LED lights up**: Relay module getting signal, physical relay may be faulty
-  **No LED**: Jumper configuration issue or wiring problem

## **What to Look For**

Take a photo of your relay board and look for:

1. **Jumper caps** - Small plastic rectangles covering 2 pins
2. **Pin headers** - Metal pins in rows (usually 2x3 or 2x4)
3. **Labels** - Text like "JD-VCC", "VCC", "H", "L", "5V", "3.3V"
4. **Missing caps** - Pins without jumper caps that others have

## **Most Likely Fix**

Based on your symptoms (software works, no clicking), **Relay 4** probably has:

1. **Missing jumper cap** for power or trigger configuration
2. **Wrong trigger level** setting (H/L jumper in wrong position)
3. **Power isolation** issue if using JD-VCC jumpers

## **Action Plan**

1. **Photo your relay board** - Document current jumper positions
2. **Compare Relay 1-3 vs Relay 4** jumper settings
3. **Copy working configuration** from Relay 1-3 to Relay 4
4. **Test immediately** after each change
5. **Report results** - What jumper changes made it work

The fact that **3 out of 4 relays work perfectly** means your wiring and code are correct - this is almost certainly a **jumper configuration issue** on **Relay 4's channel**! 