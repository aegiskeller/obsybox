# Persistent Configuration System for NINA Target Selector

## Overview
The NINA Target Selector now includes a persistent configuration system that saves user parameter changes automatically. When you modify parameters in the GUI and generate targets, your settings become the new defaults for future sessions.

## How It Works

### Configuration Storage
- User preferences are stored in `user_config.json` in the `nina_scheduling` directory
- The file is created automatically with default values on first run
- Configuration is organized into logical sections (location, magnitudes, altitudes, etc.)

### Parameter Categories
The configuration system manages these parameter groups:

**Observer Location**
- Latitude/Longitude coordinates
- Elevation and timezone offset

**Magnitude Limits**
- Minimum and maximum star magnitudes for target selection

**Altitude Constraints**
- Minimum altitude at minima time
- Minimum altitude during observation window

**Declination Limits**
- Northern and southern declination boundaries

**Timing Parameters**
- Observation window duration
- Target spacing
- Maximum targets per night

**Tracking Parameters**
- Drift tolerance for centering

**Azimuth Preferences**
- Allowed direction constraints (N, NE, NW, E, W, SE, SW, S)

### Automatic Saving
- Every time you click "Generate Targets", your current GUI settings are automatically saved
- No manual "Save" button needed - settings persist immediately
- Next time you open the GUI, your last-used settings will be loaded

### Reset to Defaults
- Click the "⚙️ Reset Defaults" button to restore original factory settings
- Requires confirmation to prevent accidental resets
- Useful if you want to start fresh or if settings become corrupted

## Technical Implementation

### Files Added
- `config.py`: Configuration management module
- `user_config.json`: User preferences storage file (auto-created)

### Files Modified
- `findTargets.py`: Now loads parameters from config file with fallback to hardcoded values
- `target_selector_gui.py`: Enhanced with config loading/saving and reset functionality

### Integration Points
1. **Startup**: GUI loads saved parameters from `user_config.json`
2. **Generation**: Parameters are saved automatically when generating targets
3. **Reset**: "Reset Defaults" button restores factory settings
4. **Fallback**: System gracefully handles missing config files or modules

## Benefits
- **Convenience**: No need to re-enter your preferred settings each session
- **Reliability**: Settings persist across program restarts and system reboots
- **Flexibility**: Easy to experiment with different parameters knowing you can reset
- **Backwards Compatibility**: Works even if config system fails (uses hardcoded fallbacks)

## Configuration File Location
```
c:\Users\aegis\Documents\obsybox\nina_scheduling\user_config.json
```

This file can be backed up, shared, or manually edited if needed (though GUI modification is recommended).

## Troubleshooting
- If settings seem wrong, use "Reset Defaults" to restore factory values
- If GUI fails to start, delete `user_config.json` to force recreation with defaults
- Configuration errors are logged to the GUI log window
- System falls back to hardcoded values if config system fails

The persistent configuration system makes the NINA Target Selector much more user-friendly by remembering your preferred observatory settings and target selection criteria.