# NINA Target Selector Launcher Updates

## Overview
Updated the desktop launcher and batch file with enhanced error handling, better diagnostics, and improved PowerShell compatibility.

## Files Updated

### 1. `run_target_gui.bat` (Enhanced Batch Launcher)
**New Features:**
- Enhanced error messages with troubleshooting tips
- Better visual formatting with separators and clear information display
- Full path usage to avoid PowerShell execution conflicts
- Detailed startup information showing current features
- Comprehensive error handling for common issues

**Improvements:**
- Window title updates to show current status
- Checks for both virtual environment and GUI script existence
- Provides specific solutions for common problems
- Full paths used throughout to prevent path resolution issues

### 2. `create_desktop_shortcut.ps1` (PowerShell Shortcut Creator)
**New Features:**
- Better error handling with try/catch blocks
- Verification of target files before creating shortcuts
- Enhanced success/failure messaging
- Updated description including new features

**Improvements:**
- More robust COM object handling
- Better icon selection logic
- Comprehensive status reporting
- Multiple launch option documentation

## Launch Options

### Option 1: Desktop Shortcut (Recommended)
- Double-click "NINA Target Selector" icon on desktop
- Uses the enhanced batch file launcher
- Shows startup information and diagnostics

### Option 2: Batch File Direct
- Navigate to `nina_scheduling` folder
- Double-click `run_target_gui.bat`
- Same enhanced experience as desktop shortcut

### Option 3: Command Line
```cmd
cd "C:\Users\aegis\Documents\obsybox\nina_scheduling"
venv\Scripts\python.exe target_selector_gui.py
```

## Troubleshooting Features

### Built-in Diagnostics
The launcher now provides specific error messages and solutions for:

1. **Missing Virtual Environment**
   - Clear error message with setup instructions
   - Exact commands to recreate the environment

2. **Missing Python Packages**
   - Instructions for reinstalling requirements
   - Specific pip commands provided

3. **File Permission Issues**
   - Suggests running as administrator
   - File permission troubleshooting tips

4. **Configuration Problems**
   - Instructions to reset configuration files
   - Cache clearing guidance

### Error Handling Improvements
- Exit codes properly handled
- Pause on error to show messages
- Window title reflects current status
- Full path usage prevents PowerShell conflicts

## GUI Features Highlighted
The launcher now prominently displays the enhanced GUI features:
- ✅ Persistent configuration storage
- ✅ Timezone-aware observation night calculation (UTC+10)
- ✅ Automatic date field override for var.astro.cz
- ✅ Cache management and reset options
- ✅ Enhanced error handling and diagnostics

## Testing Performed
- ✅ PowerShell execution compatibility verified
- ✅ Desktop shortcut creation tested
- ✅ Error handling scenarios validated
- ✅ Virtual environment detection confirmed
- ✅ Full path resolution working

## User Benefits
1. **Easier Troubleshooting** - Clear error messages with solutions
2. **Better Reliability** - Robust path handling and error detection
3. **Professional Experience** - Clean startup messages and status updates
4. **Multiple Launch Options** - Desktop, batch file, or command line
5. **Self-Documenting** - Built-in feature descriptions and help

The updated launcher provides a much more professional and reliable experience for starting the NINA Target Selector GUI while highlighting all the recent improvements to the application.