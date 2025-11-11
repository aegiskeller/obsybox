#!/usr/bin/env python3
"""
Emergency Observatory Shutdown Script

This script performs immediate shutdown of observatory equipment
when triggered by the safety monitor or other emergency conditions.
"""

import logging
import json
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emergency_shutdown.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def emergency_shutdown():
    """Perform emergency shutdown sequence"""
    logger.critical("=== EMERGENCY SHUTDOWN INITIATED ===")
    
    shutdown_success = True
    
    try:
        # 1. Stop telescope tracking and abort any slews
        logger.info("Step 1: Stopping telescope...")
        try:
            import win32com.client
            import pythoncom
            
            pythoncom.CoInitialize()
            
            # Try multiple telescope driver options  
            telescope_drivers = [
                "ASCOM.GS.Sky.Telescope",        # User's specific GS Sky driver
                "ASCOM.RRCIDriver.Telescope",
                "ASCOM.Simulator.Telescope", 
                "ASCOM.SiTechDLL.Telescope"
            ]
            
            telescope_stopped = False
            telescope_parked = False
            for driver in telescope_drivers:
                try:
                    telescope = win32com.client.Dispatch(driver)
                    if hasattr(telescope, 'Connected'):
                        if not telescope.Connected:
                            telescope.Connected = True
                        
                        if telescope.Connected:
                            logger.info(f"Connected to telescope: {driver}")
                            
                            # Emergency stop sequence
                            try:
                                if hasattr(telescope, 'AbortSlew'):
                                    telescope.AbortSlew()
                                    logger.info("Telescope slew aborted")
                            except Exception as e:
                                if "parked" in str(e).lower():
                                    logger.info("Telescope already parked - AbortSlew not needed")
                                else:
                                    logger.warning(f"AbortSlew failed: {e}")
                            
                            try:
                                if hasattr(telescope, 'Tracking'):
                                    telescope.Tracking = False
                                    logger.info("Telescope tracking stopped")
                            except Exception as e:
                                logger.warning(f"Could not stop tracking: {e}")
                            
                            # CRITICAL: MUST PARK BEFORE DOME CLOSURE
                            if hasattr(telescope, 'CanPark') and telescope.CanPark and hasattr(telescope, 'Park'):
                                # Check if already parked first
                                if hasattr(telescope, 'AtPark') and telescope.AtPark:
                                    logger.info("Telescope already parked - safe for dome closure")
                                    telescope_parked = True
                                else:
                                    logger.critical("CRITICAL: Parking telescope before dome closure")
                                    try:
                                        telescope.Park()
                                        
                                        # Wait for park completion with timeout
                                        import time
                                        park_timeout = 60  # 60 second timeout
                                        for i in range(park_timeout):
                                            time.sleep(1)
                                            if hasattr(telescope, 'AtPark') and telescope.AtPark:
                                                logger.info("Telescope successfully parked")
                                                telescope_parked = True
                                                break
                                            elif i % 10 == 0:  # Log every 10 seconds
                                                logger.info(f"Waiting for telescope park... ({i}s)")
                                        
                                        if not telescope_parked:
                                            logger.critical("CRITICAL: Telescope park timeout! Telescope may still be moving!")
                                            logger.critical("SAFETY DECISION: Weather unsafe but telescope position unknown")
                                            logger.critical("Manual intervention required - NOT closing dome to prevent collision")
                                            # Do NOT force telescope_parked = True
                                            # Let dome closure logic handle this safely
                                    except Exception as e:
                                        if "parked" in str(e).lower():
                                            logger.info("Telescope already parked")
                                            telescope_parked = True
                                        else:
                                            logger.error(f"Park command failed: {e}")
                            else:
                                logger.warning("Telescope does not support parking - proceeding with manual override")
                                telescope_parked = True
                            
                            telescope_stopped = True
                            break
                except Exception as e:
                    logger.debug(f"Could not use telescope driver {driver}: {e}")
                    continue
                    
            if not telescope_stopped:
                logger.error("CRITICAL: Could not stop telescope via ASCOM")
                shutdown_success = False
            elif not telescope_parked:
                logger.error("CRITICAL: Telescope not parked - UNSAFE to close dome!")
                shutdown_success = False
                
        except ImportError:
            logger.error("ASCOM not available for telescope control")
            shutdown_success = False
        except Exception as e:
            logger.error(f"Error stopping telescope: {e}")
            shutdown_success = False
            
        # 2. Close dome/roof (ONLY if telescope is safely parked)
        if telescope_parked:  # Only proceed if telescope is confirmed parked
            logger.info("Step 2: Closing dome/roof (telescope is safely parked)...")
        elif not telescope_stopped:  # No telescope detected
            logger.info("Step 2: Closing dome/roof (no telescope detected)...")
        else:
            logger.critical("SAFETY ABORT: Cannot close dome - telescope position unknown!")
            logger.critical("MANUAL INTERVENTION REQUIRED:")
            logger.critical("1. Verify telescope is clear of dome closure path")
            logger.critical("2. Manually park telescope if possible")
            logger.critical("3. Close dome only when telescope is safe")
            shutdown_success = False
            
        if telescope_parked or not telescope_stopped:
            
            try:
                dome_drivers = [
                    "RRCI.Dome",                 # Correct RRCI dome driver name
                    "ASCOM.Simulator.Dome"
                ]
                
                dome_closed = False
                for driver in dome_drivers:
                    try:
                        dome = win32com.client.Dispatch(driver)
                        if hasattr(dome, 'Connected') and dome.Connected:
                            if hasattr(dome, 'CloseShutter'):
                                dome.CloseShutter()
                            elif hasattr(dome, 'ShutterStatus'):
                                # Some drivers have different methods
                                dome.ShutterStatus = 1  # Closed
                            logger.info(f"Dome close initiated via {driver}")
                            dome_closed = True
                            break
                    except Exception as e:
                        logger.debug(f"Could not use dome driver {driver}: {e}")
                        continue
                        
                if not dome_closed:
                    logger.critical("🚨 CRITICAL DOME FAILURE: Telescope is safely parked but DOME FAILED TO CLOSE!")
                    logger.critical("⚠️  EQUIPMENT EXPOSURE RISK: Dome is still OPEN during unsafe weather!")
                    logger.critical("🔧 IMMEDIATE MANUAL ACTION REQUIRED:")
                    logger.critical("   1. Manually close dome using physical controls")
                    logger.critical("   2. Check dome power and ASCOM driver connections") 
                    logger.critical("   3. Verify dome hardware is operational")
                    logger.critical("   4. Consider emergency power shutdown if dome cannot be closed")
                    
                    # Send high priority MQTT alert
                    try:
                        import paho.mqtt.client as mqtt
                        alert_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
                        alert_client.connect("192.168.1.49", 1883, 60)
                        
                        critical_alert = {
                            "alert": "CRITICAL_DOME_FAILURE",
                            "status": "DOME_OPEN_WEATHER_UNSAFE", 
                            "telescope": "SAFELY_PARKED",
                            "dome": "FAILED_TO_CLOSE",
                            "action_required": "IMMEDIATE_MANUAL_INTERVENTION",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        alert_client.publish("obsybox/emergency/dome_failure", json.dumps(critical_alert))
                        alert_client.publish("obsybox/alerts/critical", json.dumps(critical_alert))
                        alert_client.disconnect()
                        
                        logger.info("Critical dome failure alert sent via MQTT")
                    except Exception as mqtt_e:
                        logger.error(f"Failed to send dome failure alert: {mqtt_e}")
                    
                    # Send Pushover notification for critical dome failure
                    try:
                        from pushover_notifications import send_observatory_alert
                        
                        # Load config for Pushover settings
                        config_file = Path(__file__).parent / "nina_safety_config.json"
                        if config_file.exists():
                            with open(config_file, 'r') as f:
                                config = json.load(f)
                            
                            pushover_sent = send_observatory_alert(
                                config=config,
                                alert_type="emergency",
                                title="🚨 CRITICAL DOME FAILURE",
                                message="Telescope is safely parked but DOME FAILED TO CLOSE during unsafe weather! Manual intervention required immediately.",
                                priority="emergency",
                                extra_data={
                                    "Telescope Status": "SAFELY PARKED",
                                    "Dome Status": "FAILED TO CLOSE", 
                                    "Weather": "UNSAFE CONDITIONS",
                                    "Action Required": "MANUAL DOME CLOSURE"
                                }
                            )
                            
                            if pushover_sent:
                                logger.info("Critical dome failure alert sent via Pushover")
                            else:
                                logger.warning("Failed to send Pushover alert (check config)")
                        else:
                            logger.warning("Config file not found for Pushover alert")
                            
                    except Exception as pushover_e:
                        logger.error(f"Failed to send Pushover dome failure alert: {pushover_e}")
                    
                    shutdown_success = False
                    
            except Exception as e:
                logger.error(f"Error closing dome: {e}")
                shutdown_success = False
        else:
            logger.critical("SAFETY ABORT: Skipping dome closure - telescope not parked!")
            shutdown_success = False
            
        # 3. Turn off dew heaters and other accessories
        logger.info("Step 3: Shutting down accessories...")
        try:
            import paho.mqtt.client as mqtt
            
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            client.connect("192.168.1.49", 1883, 60)
            
            # Send shutdown commands via MQTT
            shutdown_commands = [
                ("obsybox/dewheater/command", json.dumps({"action": "shutdown"})),
                ("obsybox/power/command", json.dumps({"action": "emergency_off"})),
                ("obsybox/safety", json.dumps({
                    "status": "emergency_shutdown",
                    "timestamp": datetime.now().isoformat(),
                    "reason": "nina_safety_monitor"
                }))
            ]
            
            for topic, message in shutdown_commands:
                try:
                    client.publish(topic, message)
                    logger.info(f"Sent shutdown command to {topic}")
                except Exception as e:
                    logger.error(f"Failed to send command to {topic}: {e}")
                    
            client.disconnect()
            
        except Exception as e:
            logger.error(f"Error shutting down accessories: {e}")
            shutdown_success = False
            
        # 4. Kill NINA process if still running
        logger.info("Step 4: Stopping NINA process...")
        try:
            import subprocess
            result = subprocess.run(
                ["taskkill", "/F", "/IM", "NINA.exe"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("NINA process terminated")
            else:
                logger.info("NINA process was not running")
        except Exception as e:
            logger.error(f"Error stopping NINA process: {e}")
            
        # 5. Log final status
        if shutdown_success:
            logger.info("=== EMERGENCY SHUTDOWN COMPLETED SUCCESSFULLY ===")
        else:
            logger.warning("=== EMERGENCY SHUTDOWN COMPLETED WITH ERRORS ===")
            
        # 6. Send final notifications
        try:
            # Send Pushover notification for emergency shutdown completion
            from pushover_notifications import send_observatory_alert
            
            # Load config for Pushover settings
            config_file = Path(__file__).parent / "nina_safety_config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                if shutdown_success:
                    # Success notification
                    send_observatory_alert(
                        config=config,
                        alert_type="critical",
                        title="🛡️ Emergency Shutdown Complete",
                        message="Observatory emergency shutdown completed successfully. All systems safely shut down.",
                        priority="critical",
                        extra_data={
                            "Telescope": "Parked and safe",
                            "Dome": "Closed and secure",
                            "NINA": "Process terminated",
                            "Accessories": "Shutdown complete"
                        }
                    )
                    logger.info("Emergency shutdown success notification sent via Pushover")
                else:
                    # Failure notification
                    send_observatory_alert(
                        config=config,
                        alert_type="emergency",
                        title="⚠️ Emergency Shutdown Errors",
                        message="Observatory emergency shutdown completed with ERRORS. Manual intervention may be required.",
                        priority="emergency",
                        extra_data={
                            "Status": "COMPLETED WITH ERRORS",
                            "Action Required": "Check logs and equipment status",
                            "Priority": "HIGH - Verify all systems safe"
                        }
                    )
                    logger.info("Emergency shutdown error notification sent via Pushover")
                    
        except Exception as e:
            logger.error(f"Could not send final Pushover notification: {e}")
            
    except Exception as e:
        logger.critical(f"Emergency shutdown failed: {e}")
        import traceback
        traceback.print_exc()

def manual_override_dome_closure():
    """Manual override to close dome when telescope position is confirmed safe"""
    logger.critical("=== MANUAL OVERRIDE DOME CLOSURE ===")
    logger.warning("This should only be used when telescope position has been manually verified!")
    
    try:
        import win32com.client
        import pythoncom
        
        pythoncom.CoInitialize()
        
        dome_drivers = ["RRCI.Dome", "ASCOM.Simulator.Dome"]
        
        for driver in dome_drivers:
            try:
                dome = win32com.client.Dispatch(driver)
                if hasattr(dome, 'Connected') and dome.Connected:
                    if hasattr(dome, 'CloseShutter'):
                        dome.CloseShutter()
                        logger.info(f"Manual dome closure initiated via {driver}")
                        return True
            except Exception as e:
                logger.debug(f"Could not use dome driver {driver}: {e}")
                continue
                
        logger.error("Manual dome closure failed - no working dome drivers")
        return False
        
    except Exception as e:
        logger.error(f"Manual dome closure error: {e}")
        return False
        
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force-dome-close":
        manual_override_dome_closure()
    else:
        emergency_shutdown()