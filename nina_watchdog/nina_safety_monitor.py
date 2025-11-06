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
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "nina_log_paths": [
                r"C:\Users\aegis\AppData\Local\NINA\Logs",
                r"C:\ProgramData\NINA\Logs",
                r"C:\Users\aegis\Documents\NINA\Logs"
            ],
            "max_inactive_minutes": 15,  # Trigger shutdown if no activity for 15 minutes
            "check_interval_seconds": 60,  # Check every 60 seconds
            "emergency_shutdown_script": r"C:\Users\aegis\Documents\obsybox\nina_safetymon\emergency_shutdown.py",
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
            
            # Also check for recent log entries
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read last few lines to check for recent activity
                    lines = f.readlines()
                    if len(lines) > 0:
                        # Try to parse timestamp from last line
                        last_line = lines[-1].strip()
                        # NINA logs typically start with timestamp
                        # Format varies, but often like: "2025-11-06 20:30:15.123"
                        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
                            try:
                                timestamp_str = last_line[:19]  # First 19 chars usually timestamp
                                last_entry_time = datetime.strptime(timestamp_str, fmt)
                                time_since_entry = datetime.now() - last_entry_time
                                
                                if time_since_entry.total_seconds() / 60 < self.config["max_inactive_minutes"]:
                                    self.last_nina_activity = datetime.now()
                                    return True
                                break
                            except ValueError:
                                continue
                                
            except Exception as e:
                logger.debug(f"Could not parse log content: {e}")
                
            # Fall back to file modification time
            if time_since_modified.total_seconds() / 60 < self.config["max_inactive_minutes"]:
                self.last_nina_activity = datetime.now()
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking log activity: {e}")
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
            
    def check_sun_altitude(self) -> bool:
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
        """Run one monitoring cycle"""
        logger.info("Running safety monitoring cycle...")
        
        issues = []
        
        # Check NINA process
        if self.config["safety_checks"]["monitor_nina_process"]:
            if not self.check_nina_process():
                issues.append("NINA process not running")
                
        # Check log activity
        if self.config["safety_checks"]["monitor_log_activity"]:
            if not self.check_log_activity():
                issues.append("No recent NINA log activity")
                
        # Check weather safety
        if self.config["safety_checks"]["check_weather_safety"]:
            if not self.check_weather_safety():
                issues.append("Weather conditions unsafe")
                
        # Check sun altitude
        if self.config["safety_checks"]["check_sun_altitude"]:
            if not self.check_sun_altitude():
                issues.append("Sun above horizon")
                
        if issues:
            logger.warning(f"Safety issues detected: {', '.join(issues)}")
            
            # If NINA is unresponsive AND conditions are unsafe, trigger shutdown
            nina_issues = [i for i in issues if "NINA" in i]
            if nina_issues and len(issues) > len(nina_issues):
                self.emergency_shutdown()
        else:
            logger.info("All safety checks passed")
            self.shutdown_triggered = False  # Reset if conditions are good
            
    def run(self):
        """Main monitoring loop"""
        logger.info("Starting NINA Safety Monitor")
        logger.info(f"Monitoring interval: {self.config['check_interval_seconds']} seconds")
        logger.info(f"Max inactive time: {self.config['max_inactive_minutes']} minutes")
        
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