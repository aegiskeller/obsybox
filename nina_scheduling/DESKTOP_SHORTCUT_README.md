# NINA Target Selector Desktop Shortcut

## What Was Created

✅ **Desktop Shortcut**: "NINA Target Selector" icon on your desktop
✅ **Batch File**: `run_target_gui.bat` - launcher script
✅ **Setup Script**: `create_desktop_shortcut.ps1` - PowerShell script to create shortcuts

## How to Use

### Method 1: Desktop Icon (Easiest)
1. **Double-click** the "NINA Target Selector" icon on your desktop
2. The GUI will open automatically with the correct virtual environment

### Method 2: Batch File
1. Navigate to: `C:\Users\aegis\Documents\obsybox\nina_scheduling`
2. Double-click `run_target_gui.bat`

### Method 3: Manual Launch
1. Open PowerShell or Command Prompt
2. Navigate to: `C:\Users\aegis\Documents\obsybox\nina_scheduling`
3. Run: `C:\Users\aegis\Documents\obsybox\nina_scheduling\venv\Scripts\python.exe target_selector_gui.py`

## Troubleshooting

### If the GUI doesn't start:
1. **Check virtual environment**: Make sure `venv` folder exists in the nina_scheduling directory
2. **Check dependencies**: Run the batch file from a terminal to see any error messages
3. **Reinstall packages**: If needed, run:
   ```
   cd "C:\Users\aegis\Documents\obsybox\nina_scheduling"
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

### If you see "Virtual environment not found":
The batch file will show this message if the `venv` folder is missing. To fix:
1. Open PowerShell in the nina_scheduling directory
2. Run: `python -m venv venv`
3. Install packages: `.\venv\Scripts\python.exe -m pip install -r requirements.txt`

### If you need to recreate the desktop shortcut:
1. Delete the existing "NINA Target Selector" icon from your desktop
2. Navigate to: `C:\Users\aegis\Documents\obsybox\nina_scheduling`
3. Run: `PowerShell -ExecutionPolicy Bypass -File create_desktop_shortcut.ps1`

## What the Batch File Does

The `run_target_gui.bat` file:
1. Changes to the correct directory
2. Checks if the virtual environment exists
3. Runs the GUI using the virtual environment's Python
4. Shows any error messages if something goes wrong
5. Pauses on errors so you can see what happened

## Features Available in the GUI

- 🎯 **Target Generation**: Generate tonight's eclipsing binary targets
- 📊 **Airmass Plot**: Visual airmass curves with minima timing (orange markers)
- 💾 **NINA Export**: Create NINA-compatible JSON sequence files
- 📅 **Database Tracking**: Record scheduled targets for observation tracking
- ⚙️ **Configuration**: Adjust location, altitude limits, and timing parameters

The enhanced GUI now includes orange markers on the airmass plot showing the exact eclipse minima times, making it easier to plan your observations!