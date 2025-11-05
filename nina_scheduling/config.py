"""
Configuration manager for NINA Target Selector
Handles loading/saving user preferences to persistent storage
"""

import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "user_config.json"

# Default configuration values
DEFAULT_CONFIG = {
    "observer_location": {
        "latitude": -35.0,
        "longitude": 149.08,
        "elevation": 598,
        "timezone_offset": 10
    },
    "magnitude_limits": {
        "mag_min": 10.0,
        "mag_max": 12.5
    },
    "altitude_constraints": {
        "min_altitude": 45.0,
        "min_altitude_during_obs": 30.0
    },
    "declination_limits": {
        "min_declination": -40.0,
        "max_declination": 0.0
    },
    "timing_parameters": {
        "observation_window": 4.0,
        "target_spacing": 4.0,
        "max_targets_per_night": 2
    },
    "tracking_parameters": {
        "center_after_drift_arcmin": 1.5
    },
    "azimuth_preferences": {
        "allowed_azimuths": ["N", "NE", "NW", "E", "W"]
    },
    "target_constraints": {
        "allow_g_targets": True
    },
    "export_settings": {
        "nina_export_base_dir": r"C:\Users\aegis\Documents\N.I.N.A\Targets\VarStars"
    }
}

def load_config():
    """Load configuration from file, create with defaults if doesn't exist"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # Merge with defaults to handle any missing keys
            return merge_with_defaults(config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        # Create default config file
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False

def merge_with_defaults(user_config):
    """Merge user config with defaults to handle missing keys"""
    merged = DEFAULT_CONFIG.copy()
    
    # Deep merge each section
    for section, values in user_config.items():
        if section in merged and isinstance(values, dict):
            merged[section].update(values)
        else:
            merged[section] = values
    
    return merged

def get_flat_config():
    """Get configuration as flat dictionary for compatibility with findTargets.py"""
    config = load_config()
    
    return {
        'LATITUDE': config['observer_location']['latitude'],
        'LONGITUDE': config['observer_location']['longitude'],
        'ELEVATION': config['observer_location']['elevation'],
        'TIMEZONE_OFFSET': config['observer_location']['timezone_offset'],
        'MAG_MIN': config['magnitude_limits']['mag_min'],
        'MAG_MAX': config['magnitude_limits']['mag_max'],
        'MIN_ALTITUDE': config['altitude_constraints']['min_altitude'],
        'MIN_ALTITUDE_DURING_OBS': config['altitude_constraints']['min_altitude_during_obs'],
        'MIN_DECLINATION': config['declination_limits']['min_declination'],
        'MAX_DECLINATION': config['declination_limits']['max_declination'],
        'OBSERVATION_WINDOW': config['timing_parameters']['observation_window'],
        'TARGET_SPACING': config['timing_parameters']['target_spacing'],
        'MAX_TARGETS_PER_NIGHT': config['timing_parameters']['max_targets_per_night'],
        'CENTER_AFTER_DRIFT_ARCMIN': config['tracking_parameters']['center_after_drift_arcmin'],
        'ALLOWED_AZIMUTHS': config['azimuth_preferences']['allowed_azimuths'],
        'ALLOW_G_TARGETS': config['target_constraints']['allow_g_targets'],
        'NINA_EXPORT_BASE_DIR': config['export_settings']['nina_export_base_dir']
    }

def update_config_from_gui_values(gui_values):
    """Update config with values from GUI and save"""
    config = load_config()
    
    # Update location
    config['observer_location']['latitude'] = gui_values.get('latitude', config['observer_location']['latitude'])
    config['observer_location']['longitude'] = gui_values.get('longitude', config['observer_location']['longitude'])
    
    # Update magnitude limits
    config['magnitude_limits']['mag_min'] = gui_values.get('mag_min', config['magnitude_limits']['mag_min'])
    config['magnitude_limits']['mag_max'] = gui_values.get('mag_max', config['magnitude_limits']['mag_max'])
    
    # Update altitude constraints
    config['altitude_constraints']['min_altitude'] = gui_values.get('min_altitude', config['altitude_constraints']['min_altitude'])
    config['altitude_constraints']['min_altitude_during_obs'] = gui_values.get('min_altitude_during_obs', config['altitude_constraints']['min_altitude_during_obs'])
    
    # Update declination limits
    config['declination_limits']['min_declination'] = gui_values.get('min_declination', config['declination_limits']['min_declination'])
    config['declination_limits']['max_declination'] = gui_values.get('max_declination', config['declination_limits']['max_declination'])
    
    # Update timing parameters
    config['timing_parameters']['observation_window'] = gui_values.get('observation_window', config['timing_parameters']['observation_window'])
    config['timing_parameters']['target_spacing'] = gui_values.get('target_spacing', config['timing_parameters']['target_spacing'])
    config['timing_parameters']['max_targets_per_night'] = gui_values.get('max_targets_per_night', config['timing_parameters']['max_targets_per_night'])
    
    # Update azimuth preferences
    if 'allowed_azimuths' in gui_values:
        config['azimuth_preferences']['allowed_azimuths'] = gui_values['allowed_azimuths']
    
    # Update target constraints
    if 'allow_g_targets' in gui_values:
        config['target_constraints']['allow_g_targets'] = gui_values['allow_g_targets']
    
    return save_config(config)