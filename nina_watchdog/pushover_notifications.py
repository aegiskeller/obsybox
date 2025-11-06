#!/usr/bin/env python3
"""
Pushover Notification Module for NINA Safety Monitor

Sends critical observatory alerts via Pushover push notifications.
Supports different priority levels and emergency alerts.
"""

import requests
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class PushoverNotifier:
    """Handle Pushover push notifications for observatory alerts"""
    
    def __init__(self, app_token: str, user_key: str):
        """
        Initialize Pushover notifier
        
        Args:
            app_token: Pushover application token
            user_key: Pushover user/group key
        """
        self.app_token = app_token
        self.user_key = user_key
        self.api_url = "https://api.pushover.net/1/messages.json"
        
    def send_notification(self, 
                         title: str, 
                         message: str, 
                         priority: int = 0,
                         sound: Optional[str] = None,
                         url: Optional[str] = None,
                         url_title: Optional[str] = None,
                         retry: int = 60,
                         expire: int = 3600) -> bool:
        """
        Send a push notification via Pushover
        
        Args:
            title: Notification title
            message: Notification message
            priority: Priority level (-2 to 2)
                     -2: Lowest (no sound/vibration)
                     -1: Quiet 
                      0: Normal (default)
                      1: High priority
                      2: Emergency (requires acknowledgment)
            sound: Custom sound name
            url: URL to open when notification is tapped
            url_title: Title for the URL
            retry: Retry interval for emergency notifications (30-86400 seconds)
            expire: Expiry time for emergency notifications (max 86400 seconds)
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Prepare notification data
            data = {
                "token": self.app_token,
                "user": self.user_key,
                "title": title,
                "message": message,
                "priority": priority
            }
            
            # Add optional parameters
            if sound:
                data["sound"] = sound
            if url:
                data["url"] = url
            if url_title:
                data["url_title"] = url_title
                
            # Emergency notifications require retry and expire
            if priority == 2:
                data["retry"] = max(30, min(retry, 86400))  # 30s to 24h
                data["expire"] = max(30, min(expire, 86400))  # 30s to 24h
            
            # Send the notification
            response = requests.post(self.api_url, data=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == 1:
                    logger.info(f"Pushover notification sent: {title}")
                    return True
                else:
                    logger.error(f"Pushover API error: {result}")
                    return False
            else:
                logger.error(f"Pushover HTTP error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Pushover network error: {e}")
            return False
        except Exception as e:
            logger.error(f"Pushover notification error: {e}")
            return False

def send_observatory_alert(config: Dict[str, Any], 
                          alert_type: str, 
                          title: str, 
                          message: str, 
                          priority: str = "normal",
                          extra_data: Optional[Dict] = None) -> bool:
    """
    Send observatory alert via Pushover using configuration
    
    Args:
        config: Configuration dictionary with Pushover settings
        alert_type: Type of alert (emergency, critical, warning, info)
        title: Alert title
        message: Alert message
        priority: Priority level name (emergency, critical, normal, quiet)
        extra_data: Additional data to include in message
        
    Returns:
        True if notification sent successfully
    """
    try:
        # Check if Pushover is enabled
        pushover_config = config.get("pushover", {})
        if not pushover_config.get("enabled", False):
            logger.debug("Pushover notifications disabled")
            return False
            
        app_token = pushover_config.get("app_token")
        user_key = pushover_config.get("user_key")
        
        if not app_token or not user_key:
            logger.warning("Pushover credentials not configured")
            return False
            
        if app_token == "YOUR_PUSHOVER_APP_TOKEN_HERE" or user_key == "YOUR_PUSHOVER_USER_KEY_HERE":
            logger.warning("Pushover credentials not set (using default placeholders)")
            return False
        
        # Map priority names to numbers
        priority_map = {
            "emergency": pushover_config.get("emergency_priority", 2),
            "critical": pushover_config.get("critical_priority", 1), 
            "normal": pushover_config.get("normal_priority", 0),
            "quiet": -1,
            "silent": -2
        }
        
        priority_num = priority_map.get(priority, 0)
        
        # Create notifier
        notifier = PushoverNotifier(app_token, user_key)
        
        # Enhance message with extra data
        full_message = message
        if extra_data:
            full_message += "\n\nDetails:"
            for key, value in extra_data.items():
                full_message += f"\n• {key}: {value}"
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message += f"\n\nTime: {timestamp}"
        
        # Select sound based on alert type
        sound_map = {
            "emergency": "siren",
            "critical": "alien", 
            "warning": "persistent",
            "info": None
        }
        sound = sound_map.get(alert_type)
        
        # Set retry/expire for emergency alerts
        retry = 60 if priority_num == 2 else 60
        expire = 3600 if priority_num == 2 else 3600  # 1 hour
        
        # Send notification
        return notifier.send_notification(
            title=f"🏠 Observatory: {title}",
            message=full_message,
            priority=priority_num,
            sound=sound,
            retry=retry,
            expire=expire
        )
        
    except Exception as e:
        logger.error(f"Failed to send observatory alert: {e}")
        return False

def test_pushover_connection(config: Dict[str, Any]) -> bool:
    """
    Test Pushover connection with a simple message
    
    Args:
        config: Configuration dictionary with Pushover settings
        
    Returns:
        True if test successful
    """
    return send_observatory_alert(
        config=config,
        alert_type="info",
        title="Test Connection",
        message="This is a test notification from NINA Safety Monitor. If you receive this, Pushover is working correctly!",
        priority="normal"
    )

if __name__ == "__main__":
    # Test script
    import json
    
    # Load config for testing
    try:
        with open("nina_safety_config.json", "r") as f:
            config = json.load(f)
        
        print("Testing Pushover connection...")
        if test_pushover_connection(config):
            print("✅ Pushover test successful!")
        else:
            print("❌ Pushover test failed!")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        print("\nMake sure to:")
        print("1. Configure your Pushover app token and user key in nina_safety_config.json")
        print("2. Set 'enabled': true in the pushover section")
        print("3. Install requests: pip install requests")