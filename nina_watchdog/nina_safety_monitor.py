#!/usr/bin/env python3
"""
NINA Safety Monitor - External watchdog for NINA astrophotography software

Monitors NINA log files for activity and triggers observatory safety shutdown
if NINA becomes unresponsive or stops logging for too long.

This is a critical safety system to prevent equipment damage.
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import subprocess
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nina_safety_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NINASafetyMonitor:
    def __init__(self, config_file: str = "nina_safety_config.json"):
        """Initialize the NINA safety monitor"""
        self.config_file = Path(config_file)
        self.load_config()
        self.last_nina_activity = None
        self.shutdown_triggered = False
        self.tracking_stopped = False
        self.dawn_shutdown_triggered = False
        self.sun_altitude_shutdown_triggered = False
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "nina_log_paths": [
                r"C:\Users\aegis\AppData\Local\NINA\Logs",
                r"C:\ProgramData\NINA\Logs",
                r"C:\Users\aegis\Documents\NINA\Logs"
            ],
            "safety_timeouts": {
                "tracking_stop_minutes": 51,     # Stop tracking after 51 min of inactivity in safe conditions
                "dawn_shutdown_minutes": 15,     # Park & close dome after 15 min past astronomical dawn
                "emergency_shutdown_minutes": 15, # Emergency shutdown after 15 min in unsafe conditions
                "sun_altitude_shutdown_minutes": 5 # Immediate shutdown after 5 min when sun > -12° (civil twilight)
            },
            "check_interval_seconds": 60,  # Check every 60 seconds
            "emergency_shutdown_script": r"C:\Users\aegis\Documents\obsybox\nina_watchdog\emergency_shutdown.py",
            "ascom_telescope_driver": "ASCOM.RRCIDriver.Telescope",
            "ascom_dome_driver": "RRCI.Dome",
            "nina_process_name": "NINA.exe",
            "safety_checks": {
                "monitor_nina_process": True,
                "monitor_log_activity": True,
                "check_weather_safety": True,
                "check_sun_altitude": True
            },
            "mqtt_broker": "192.168.1.49",
            "mqtt_port": 1883,
            "mqtt_safety_topic": "obsybox/safety_monitor",
            "notification_email": None,  # Add email for notifications
            "pushover": {
                "enabled": False,  # Set to True and configure tokens to enable
                "app_token": "YOUR_PUSHOVER_APP_TOKEN_HERE",
                "user_key": "YOUR_PUSHOVER_USER_KEY_HERE",
                "emergency_priority": 2,
                "critical_priority": 1,
                "normal_priority": 0
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    self.config = {**default_config, **user_config}
            except Exception as e:
                logger.error(f"Error loading config: {e}, using defaults")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
            
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
    def find_latest_nina_log(self) -> Optional[Path]:
        """Find the most recent NINA log file"""
        latest_log = None
        latest_time = 0
        
        for log_path in self.config["nina_log_paths"]:
            log_dir = Path(log_path)
            if not log_dir.exists():
                continue
                
            # Look for log files (typically .log or .txt)
            for pattern in ["*.log", "*.txt"]:
                for log_file in log_dir.glob(pattern):
                    try:
                        mtime = log_file.stat().st_mtime
                        if mtime > latest_time:
                            latest_time = mtime
                            latest_log = log_file
                    except:
                        continue
                        
        return latest_log
        
    def check_nina_process(self) -> bool:
        """Check if NINA process is running"""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {self.config['nina_process_name']}"],
                capture_output=True,
                text=True
            )
            return self.config['nina_process_name'] in result.stdout
        except Exception as e:
            logger.error(f"Error checking NINA process: {e}")
            return False
            
    def get_activity_timeout_minutes(self) -> float:
        """Get the minimum activity timeout from tiered safety timeouts"""
        safety_timeouts = self.config.get("safety_timeouts", {})
        return min(
            safety_timeouts.get("tracking_stop_minutes", 51),
            safety_timeouts.get("dawn_shutdown_minutes", 15),
            safety_timeouts.get("emergency_shutdown_minutes", 15)
        )
    
    def check_log_activity(self) -> bool:
        """Check if NINA has been active recently by examining log files"""
        try:
            log_file = self.find_latest_nina_log()
            if not log_file:
                logger.warning("No NINA log files found")
                return False
                
            # Check file modification time
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            time_since_modified = datetime.now() - mtime
            
            # Check if NINA is in a waiting state (Wait for Time instruction)
            if self.check_nina_waiting_state(log_file):
                logger.info("NINA is in Wait for Time state - extending activity window")
                self.last_nina_activity = datetime.now()
                return True
            
            # Also check for recent log entries
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last few lines to check for recent activity
                    lines = f.readlines()
                    if len(lines) > 0:
                        # Try to parse timestamp from last line
                        last_line = lines[-1].strip()
                        # NINA logs use format: 2025-11-02T18:57:48.0157|INFO|...
                        try:
                            if '|' in last_line and 'T' in last_line[:20]:
                                # NINA log format with T separator
                                timestamp_part = last_line.split('|')[0]
                                # Handle with or without milliseconds
                                if '.' in timestamp_part:
                                    timestamp_str = timestamp_part.split('.')[0]  # Remove milliseconds
                                else:
                                    timestamp_str = timestamp_part
                                last_entry_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                            else:
                                # Fallback to standard format
                                timestamp_str = last_line[:19]
                                last_entry_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            
                            time_since_entry = datetime.now() - last_entry_time
                            
                            if time_since_entry.total_seconds() / 60 < self.get_activity_timeout_minutes():
                                self.last_nina_activity = datetime.now()
                                return True
                                
                        except ValueError as e:
                            logger.debug(f"Could not parse timestamp from: {last_line[:30]}... Error: {e}")
                                
            except Exception as e:
                logger.debug(f"Could not parse log content: {e}")
                
            # Fall back to file modification time
            if time_since_modified.total_seconds() / 60 < self.get_activity_timeout_minutes():
                self.last_nina_activity = datetime.now()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking log activity: {e}")
            return False
    
    def check_nina_waiting_state(self, log_file) -> bool:
        """Check if NINA is currently in a Wait for Time state"""
        try:
            # Check if wait detection is enabled
            wait_config = self.config.get("wait_detection", {})
            if not wait_config.get("enable_wait_detection", True):
                return False
                
            check_lines = wait_config.get("wait_check_lines", 50)
            grace_period = wait_config.get("wait_grace_period_minutes", 120)
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Read the last portion of the log file to check for waiting states
                f.seek(0, 2)  # Go to end of file
                file_size = f.tell()
                
                # Read last 10KB or entire file if smaller
                read_size = min(10240, file_size)
                f.seek(max(0, file_size - read_size))
                content = f.read()
                
                lines = content.split('\n')
                recent_lines = lines[-check_lines:]  # Check configurable number of lines
                
                # Look for patterns indicating NINA is waiting
                waiting_patterns = [
                    "Starting Category: Utility, Item: WaitForTime",
                    "Wait for Time",
                    "Waiting for time",
                    "waiting for time", 
                    "Wait until",
                    "Waiting until",
                    "waiting until",
                    "WaitForTime",
                    "Wait for time:",
                    "Waiting for:",
                    "Wait instruction"
                ]
                
                # Also look for completion patterns that would indicate waiting is over
                completion_patterns = [
                    "Finishing Category: Utility, Item: WaitForTime",
                    "Wait completed",
                    "Wait finished", 
                    "Time reached",
                    "Wait instruction completed",
                    "Moving to next",
                    "Continuing sequence"
                ]
                
                wait_found = False
                completion_found = False
                wait_time = None
                completion_time = None
                
                for line in recent_lines:
                    line_lower = line.lower()
                    
                    # Extract timestamp from line if possible
                    # NINA format: 2025-11-02T18:57:48.0157|INFO|...
                    try:
                        if '|' in line and 'T' in line[:20]:
                            # NINA log format with T separator
                            timestamp_part = line.split('|')[0]
                            # Handle with or without milliseconds
                            if '.' in timestamp_part:
                                timestamp_str = timestamp_part.split('.')[0]  # Remove milliseconds
                            else:
                                timestamp_str = timestamp_part
                            line_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                        else:
                            # Fallback to standard format
                            timestamp_str = line[:19]
                            line_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        continue
                        
                    # Check for waiting patterns
                    for pattern in waiting_patterns:
                        if pattern.lower() in line_lower:
                            wait_found = True
                            if wait_time is None or line_time > wait_time:
                                wait_time = line_time
                                
                    # Check for completion patterns  
                    for pattern in completion_patterns:
                        if pattern.lower() in line_lower:
                            completion_found = True
                            if completion_time is None or line_time > completion_time:
                                completion_time = line_time
                
                # If we found a wait and either no completion or wait is more recent
                if wait_found and wait_time:
                    # Check if wait is within grace period
                    time_since_wait = datetime.now() - wait_time
                    if time_since_wait.total_seconds() / 60 > grace_period:
                        logger.warning(f"Wait state detected but exceeded grace period of {grace_period} minutes")
                        return False
                        
                    if not completion_found:
                        logger.info(f"Found active wait state from {wait_time} (no completion found)")
                        return True
                    elif completion_time and wait_time > completion_time:
                        logger.info(f"Found wait state from {wait_time} more recent than completion at {completion_time}")
                        return True
                    else:
                        logger.debug(f"Wait state found but completed at {completion_time}")
                        
                return False
                
        except Exception as e:
            logger.debug(f"Error checking waiting state: {e}")
            return False
            
    def check_weather_safety(self) -> bool:
        """Check weather safety via MQTT"""
        try:
            import paho.mqtt.client as mqtt
            
            safety_status = {"safe": True}  # Default to safe if can't check
            
            def on_message(client, userdata, message):
                try:
                    payload = json.loads(message.payload.decode())
                    if 'safe' in payload:
                        safety_status["safe"] = payload["safe"]
                except:
                    pass
                    
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            client.on_message = on_message
            client.connect(self.config["mqtt_broker"], self.config["mqtt_port"], 60)
            client.subscribe("obsybox/weathersafety")
            client.loop_start()
            
            # Wait briefly for message
            time.sleep(2)
            client.loop_stop()
            client.disconnect()
            
            return safety_status["safe"]
            
        except Exception as e:
            logger.warning(f"Could not check weather safety: {e}")
            return True  # Default to safe if can't check
            
    def check_astronomical_dawn(self) -> bool:
        """Check if it's past astronomical dawn (sun > -18 degrees)"""
        try:
            from astropy.coordinates import EarthLocation, AltAz, get_sun
            from astropy.time import Time
            import astropy.units as u
            
            # Observatory location from config
            obs_config = self.config.get("observatory_location", {})
            lat = obs_config.get("latitude", -35.0)
            lon = obs_config.get("longitude", 150.0)
            elevation = obs_config.get("elevation_meters", 100)
            location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=elevation*u.m)
            
            now = Time.now()
            sun_altaz = get_sun(now).transform_to(AltAz(obstime=now, location=location))
            sun_altitude = sun_altaz.alt.degree
            
            # Astronomical dawn is when sun is above -18 degrees
            is_past_dawn = sun_altitude > -18.0
            logger.info(f"Sun altitude: {sun_altitude:.1f}°, Past astronomical dawn: {is_past_dawn}")
            
            return is_past_dawn
            
        except Exception as e:
            logger.warning(f"Could not check astronomical dawn: {e}")
            return False  # Default to False if can't check
    
    def check_sun_altitude(self) -> tuple:
        """Check sun altitude and return (is_safe, altitude_degrees, description)"""
        try:
            from astropy.coordinates import EarthLocation, AltAz, get_sun
            from astropy.time import Time
            import astropy.units as u
            
            # Observatory location from config
            obs_config = self.config.get("observatory_location", {})
            lat = obs_config.get("latitude", -35.0)
            lon = obs_config.get("longitude", 150.0)
            elevation = obs_config.get("elevation_meters", 100)
            location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=elevation*u.m)
            
            now = Time.now()
            sun_altaz = get_sun(now).transform_to(AltAz(obstime=now, location=location))
            sun_altitude = sun_altaz.alt.degree
            
            # Determine safety and description
            if sun_altitude < -18.0:
                return True, sun_altitude, f"{sun_altitude:.1f}° (astronomical night)"
            elif sun_altitude < -12.0:
                return True, sun_altitude, f"{sun_altitude:.1f}° (nautical twilight)"
            elif sun_altitude < -6.0:
                return False, sun_altitude, f"{sun_altitude:.1f}° (civil twilight)"
            elif sun_altitude < 0.0:
                return False, sun_altitude, f"{sun_altitude:.1f}° (sunset/sunrise)"
            else:
                return False, sun_altitude, f"{sun_altitude:.1f}° (daytime)"
                
        except Exception as e:
            logger.error(f"Error checking sun altitude: {e}")
            return False, 0.0, "calculation error"
    
    def stop_telescope_tracking_only(self):
        """Stop telescope tracking without full shutdown"""
        if self.tracking_stopped:
            logger.info("Tracking already stopped")
            return
            
        logger.warning("STOPPING TELESCOPE TRACKING - NINA inactive for >51 minutes in safe conditions")
        
        try:
            import win32com.client
            import pythoncom
            
            pythoncom.CoInitialize()
            
            telescope = win32com.client.Dispatch(self.config["ascom_telescope_driver"])
            if telescope.Connected:
                telescope.Tracking = False
                logger.info("✓ Telescope tracking stopped")
                self.tracking_stopped = True
                
                # Send notification
                try:
                    from pushover_notifications import send_observatory_alert
                    send_observatory_alert(
                        config=self.config,
                        alert_type="normal",
                        title="🔭 Telescope Tracking Stopped",
                        message="NINA inactive for >51 minutes. Tracking stopped as precaution. Weather conditions are safe.",
                        priority="normal"
                    )
                except Exception as e:
                    logger.error(f"Could not send tracking stop notification: {e}")
                    
        except Exception as e:
            logger.error(f"Could not stop telescope tracking: {e}")
    
    def dawn_shutdown(self):
        """Shutdown for dawn conditions - park telescope and close dome"""
        if self.dawn_shutdown_triggered:
            logger.info("Dawn shutdown already triggered")
            return
            
        logger.warning("DAWN SHUTDOWN - NINA inactive for >15 minutes past astronomical dawn")
        self.dawn_shutdown_triggered = True
        
        try:
            # Send notification first
            try:
                from pushover_notifications import send_observatory_alert
                send_observatory_alert(
                    config=self.config,
                    alert_type="critical",
                    title="🌅 Dawn Observatory Shutdown",
                    message="NINA inactive past astronomical dawn. Parking telescope and closing dome for equipment protection.",
                    priority="critical"
                )
            except Exception as e:
                logger.error(f"Could not send dawn shutdown notification: {e}")
            
            # Park telescope and close dome
            import win32com.client
            import pythoncom
            
            pythoncom.CoInitialize()
            
            # Park telescope
            telescope = win32com.client.Dispatch(self.config["ascom_telescope_driver"])
            if telescope.Connected:
                telescope.Tracking = False
                if hasattr(telescope, 'Park'):
                    telescope.Park()
                    logger.info("✓ Telescope parked for dawn")
                else:
                    logger.warning("Telescope does not support parking")
            
            # Close dome
            dome = win32com.client.Dispatch(self.config["ascom_dome_driver"])
            if dome.Connected:
                dome.CloseShutter()
                logger.info("✓ Dome closed for dawn")
                
        except Exception as e:
            logger.error(f"Dawn shutdown failed: {e}")
            
    def sun_altitude_shutdown(self, sun_altitude, sun_description):
        """Shutdown due to sun altitude safety violation"""
        logger.critical(f"SUN ALTITUDE SHUTDOWN - Sun at {sun_description}, dome must close immediately")
        
        try:
            # Send notification first
            try:
                from pushover_notifications import send_observatory_alert
                send_observatory_alert(
                    config=self.config,
                    alert_type="emergency",
                    title="☀️ Sun Altitude Emergency Shutdown",
                    message=f"Sun altitude {sun_description}. NINA inactive during unsafe solar conditions. Emergency dome closure initiated.",
                    priority="emergency"
                )
            except Exception as e:
                logger.error(f"Could not send sun altitude shutdown notification: {e}")
            
            # Immediate shutdown actions
            import win32com.client
            import pythoncom
            
            pythoncom.CoInitialize()
            
            # Stop telescope tracking immediately
            try:
                telescope = win32com.client.Dispatch(self.config["ascom_telescope_driver"])
                if telescope.Connected:
                    telescope.Tracking = False
                    telescope.AbortSlew()
                    if hasattr(telescope, 'Park'):
                        telescope.Park()
                    logger.info("✓ Telescope stopped and parked for sun safety")
            except Exception as e:
                logger.error(f"Could not stop telescope: {e}")
                
            # Close dome immediately
            try:
                dome = win32com.client.Dispatch(self.config["ascom_dome_driver"])
                if dome.Connected:
                    dome.CloseShutter()
                    logger.info("✓ Dome closed for sun altitude safety")
            except Exception as e:
                logger.error(f"Could not close dome: {e}")
                
        except Exception as e:
            logger.error(f"Sun altitude shutdown failed: {e}")
            
    def get_inactive_minutes(self) -> float:
        """Get minutes since last NINA activity"""
        if self.last_nina_activity is None:
            return 0.0
        
        time_since = datetime.now() - self.last_nina_activity
        return time_since.total_seconds() / 60.0
        """Check if sun is below horizon (safe for observing)"""
        try:
            from astropy.coordinates import EarthLocation, get_sun, AltAz
            from astropy.time import Time
            import astropy.units as u
            
            # Use observatory location from config
            try:
                # Try to import from nina_scheduling directory
                sys.path.insert(0, str(Path(__file__).parent.parent / "nina_scheduling"))
                from config import get_flat_config
                config = get_flat_config()
                lat = config['LATITUDE']
                lon = config['LONGITUDE']
            except:
                # Fallback coordinates (Canberra area)
                lat = -35.0
                lon = 149.08
                
            location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg)
            now = Time.now()
            sun = get_sun(now)
            altaz = sun.transform_to(AltAz(obstime=now, location=location))
            
            # Sun should be below -10 degrees for safe observing
            return altaz.alt.degree < -10
            
        except Exception as e:
            logger.warning(f"Could not check sun altitude: {e}")
            return True  # Default to safe if can't check
            
    def emergency_shutdown(self):
        """Trigger emergency observatory shutdown"""
        if self.shutdown_triggered:
            logger.info("Shutdown already triggered, skipping")
            return
            
        logger.critical("TRIGGERING EMERGENCY SHUTDOWN - NINA UNRESPONSIVE")
        self.shutdown_triggered = True
        
        try:
            # Send MQTT alert
            import paho.mqtt.client as mqtt
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            client.connect(self.config["mqtt_broker"], self.config["mqtt_port"], 60)
            alert_msg = {
                "alert": "EMERGENCY_SHUTDOWN",
                "reason": "NINA_UNRESPONSIVE",
                "timestamp": datetime.now().isoformat(),
                "triggered_by": "nina_safety_monitor"
            }
            client.publish(self.config["mqtt_safety_topic"], json.dumps(alert_msg))
            client.disconnect()
            
        except Exception as e:
            logger.error(f"Could not send MQTT alert: {e}")
            
        # Send Pushover alert for NINA emergency shutdown
        try:
            from pushover_notifications import send_observatory_alert
            
            pushover_sent = send_observatory_alert(
                config=self.config,
                alert_type="critical",
                title="🚨 NINA Emergency Shutdown",
                message="NINA has become unresponsive during unsafe conditions. Emergency shutdown initiated.",
                priority="critical",
                extra_data={
                    "Trigger": "NINA unresponsive + unsafe conditions",
                    "Action": "Emergency shutdown in progress",
                    "Status": "Automatic safety response"
                }
            )
            
            if pushover_sent:
                logger.info("NINA emergency shutdown alert sent via Pushover")
            else:
                logger.warning("Failed to send Pushover alert (check config)")
                
        except Exception as e:
            logger.error(f"Failed to send Pushover emergency alert: {e}")
            
        # Run emergency shutdown script
        shutdown_script = Path(self.config["emergency_shutdown_script"])
        if shutdown_script.exists():
            try:
                subprocess.run([sys.executable, str(shutdown_script)], check=True)
                logger.info("Emergency shutdown script executed successfully")
            except Exception as e:
                logger.error(f"Emergency shutdown script failed: {e}")
        else:
            logger.error(f"Emergency shutdown script not found: {shutdown_script}")
            
        # Try direct ASCOM shutdown as backup
        try:
            self.ascom_emergency_shutdown()
        except Exception as e:
            logger.error(f"ASCOM emergency shutdown failed: {e}")
            
    def ascom_emergency_shutdown(self):
        """Emergency shutdown via ASCOM drivers"""
        try:
            import win32com.client
            import pythoncom
            
            pythoncom.CoInitialize()
            
            # Stop telescope tracking
            try:
                telescope = win32com.client.Dispatch(self.config["ascom_telescope_driver"])
                if telescope.Connected:
                    telescope.Tracking = False
                    telescope.AbortSlew()
                    logger.info("Telescope tracking stopped")
            except Exception as e:
                logger.error(f"Could not stop telescope: {e}")
                
            # Close dome/roof
            try:
                dome = win32com.client.Dispatch(self.config["ascom_dome_driver"])
                if dome.Connected:
                    dome.CloseShutter()
                    logger.info("Dome/roof closing initiated")
            except Exception as e:
                logger.error(f"Could not close dome: {e}")
                
        except ImportError:
            logger.error("ASCOM COM objects not available")
        except Exception as e:
            logger.error(f"ASCOM emergency shutdown error: {e}")
            
    def run_monitoring_cycle(self):
        """Run one monitoring cycle with tiered safety responses"""
        logger.info("Running safety monitoring cycle...")
        
        issues = []
        inactive_minutes = self.get_inactive_minutes()
        
        # Check NINA process
        if self.config["safety_checks"]["monitor_nina_process"]:
            if not self.check_nina_process():
                issues.append("NINA process not running")
                
        # Check log activity
        nina_log_inactive = False
        if self.config["safety_checks"]["monitor_log_activity"]:
            if not self.check_log_activity():
                issues.append("No recent NINA log activity")
                nina_log_inactive = True
                
        # Check weather safety
        weather_unsafe = False
        if self.config["safety_checks"]["check_weather_safety"]:
            if not self.check_weather_safety():
                issues.append("Weather conditions unsafe")
                weather_unsafe = True
                
        # Check sun altitude with detailed info
        sun_above_horizon = False
        sun_altitude = 0.0
        sun_description = "unknown"
        if self.config["safety_checks"]["check_sun_altitude"]:
            is_safe, sun_altitude, sun_description = self.check_sun_altitude()
            if not is_safe:
                issues.append(f"Sun unsafe: {sun_description}")
                sun_above_horizon = True
        
        # Check astronomical dawn
        past_astro_dawn = self.check_astronomical_dawn()
        
        # Log current status
        if issues:
            logger.warning(f"Safety issues detected: {', '.join(issues)} (Inactive: {inactive_minutes:.1f} min)")
        else:
            logger.info(f"All safety checks passed (Last activity: {inactive_minutes:.1f} min ago)")
        
        # TIERED SAFETY LOGIC (order matters - most critical first)
        
        # 1. Sun altitude emergency: NINA inactive + sun > -12° (civil twilight or worse)
        if nina_log_inactive and sun_altitude > -12.0 and inactive_minutes >= self.config["safety_timeouts"]["sun_altitude_shutdown_minutes"]:
            if not self.sun_altitude_shutdown_triggered:
                logger.critical(f"SUN ALTITUDE EMERGENCY: NINA inactive {inactive_minutes:.1f} min during {sun_description}")
                self.sun_altitude_shutdown(sun_altitude, sun_description)
                self.sun_altitude_shutdown_triggered = True
        
        # 2. Emergency shutdown: NINA inactive + unsafe weather conditions
        elif nina_log_inactive and weather_unsafe and inactive_minutes >= self.config["safety_timeouts"]["emergency_shutdown_minutes"]:
            if not self.shutdown_triggered:
                logger.critical(f"EMERGENCY: NINA inactive {inactive_minutes:.1f} min + unsafe weather conditions")
                self.emergency_shutdown()
        
        # 3. Dawn shutdown: NINA inactive + past astronomical dawn (-18°)
        elif nina_log_inactive and past_astro_dawn and not sun_above_horizon and inactive_minutes >= self.config["safety_timeouts"]["dawn_shutdown_minutes"]:
            if not self.dawn_shutdown_triggered:
                logger.warning(f"DAWN SHUTDOWN: NINA inactive {inactive_minutes:.1f} min past astronomical dawn")
                self.dawn_shutdown()
        
        # 4. Tracking stop: NINA inactive + safe conditions for 51+ minutes
        elif nina_log_inactive and not weather_unsafe and not sun_above_horizon and inactive_minutes >= self.config["safety_timeouts"]["tracking_stop_minutes"]:
            if not self.tracking_stopped:
                logger.info(f"TRACKING STOP: NINA inactive {inactive_minutes:.1f} min in safe conditions")
                self.stop_telescope_tracking_only()
        
        # Reset flags if conditions improve
        if not nina_log_inactive or inactive_minutes < 5:  # Activity resumed
            if self.tracking_stopped or self.dawn_shutdown_triggered or self.shutdown_triggered or self.sun_altitude_shutdown_triggered:
                logger.info("NINA activity resumed - resetting safety flags")
                self.tracking_stopped = False
                self.dawn_shutdown_triggered = False
                self.shutdown_triggered = False
                self.sun_altitude_shutdown_triggered = False
            
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting NINA Safety Monitor")
        logger.info(f"Monitoring interval: {self.config['check_interval_seconds']} seconds")
        logger.info(f"Tiered Safety Timeouts:")
        logger.info(f"  • Sun altitude shutdown: {self.config['safety_timeouts']['sun_altitude_shutdown_minutes']} minutes when sun > -12°")
        logger.info(f"  • Emergency shutdown (weather): {self.config['safety_timeouts']['emergency_shutdown_minutes']} minutes in unsafe weather")
        logger.info(f"  • Dawn shutdown: {self.config['safety_timeouts']['dawn_shutdown_minutes']} minutes past astronomical dawn")
        logger.info(f"  • Tracking stop (safe): {self.config['safety_timeouts']['tracking_stop_minutes']} minutes in safe conditions")
        
        # Log wait detection configuration
        wait_config = self.config.get("wait_detection", {})
        if wait_config.get("enable_wait_detection", True):
            grace_period = wait_config.get("wait_grace_period_minutes", 120)
            logger.info(f"Wait Detection: Enabled (grace period: {grace_period} minutes)")
        else:
            logger.info("Wait Detection: Disabled")
        
        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(self.config["check_interval_seconds"])
                
        except KeyboardInterrupt:
            logger.info("Safety monitor stopped by user")
        except Exception as e:
            logger.critical(f"Safety monitor crashed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    monitor = NINASafetyMonitor()
    monitor.run()