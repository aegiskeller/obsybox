import sys
import json
import pythoncom
import win32com.client
import paho.mqtt.client as mqtt
import os
import time

### to be run on the mini-pc

sys.path.append(r"C:\Program Files (x86)\Common Files\ASCOM\Platform")

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_MOUNT = "obsybox/telescope/position"
MQTT_TOPIC_CAMERA = "obsybox/camera/status"
MQTT_TOPIC_DOME = "obsybox/dome/status"
MQTT_TOPIC_FILTERWHEEL = "obsybox/filterwheel/status"
MQTT_TOPIC_FOCUSER = "obsybox/focuser/status"

DEVICE_ID_FILE = "ascom_device_ids.json"

def load_device_ids():
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r") as f:
            return json.load(f)
    return {}

def save_device_ids(ids):
    with open(DEVICE_ID_FILE, "w") as f:
        json.dump(ids, f)

def get_device_id(device_type, chooser_key=None):
    ids = load_device_ids()
    key = chooser_key if chooser_key else device_type
    if key in ids:
        return ids[key]
    pythoncom.CoInitialize()
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = device_type
    device_id = chooser.Choose(None)
    if device_id:
        ids[key] = device_id
        save_device_ids(ids)
    return device_id

def get_mount_ra_dec():
    pythoncom.CoInitialize()
    device_id = get_device_id("Telescope")
    if not device_id:
        print("No telescope selected.")
        return None, None
    scope = win32com.client.Dispatch(device_id)
    if not scope.Connected:
        scope.Connected = True
    ra = scope.RightAscension
    dec = scope.Declination
    scope.Connected = False
    return ra, dec

def get_camera_status():
    pythoncom.CoInitialize()
    device_id = get_device_id("Camera")
    if not device_id:
        print("No camera selected.")
        return {"connected": False}
    cam = win32com.client.Dispatch(device_id)
    status = {}
    try:
        cam.Connected = True
        time.sleep(1)  # Give hardware/driver time to update status
        status["connected"] = True
        status["cooler_on"] = cam.CoolerOn if hasattr(cam, "CoolerOn") else None
        status["cooler_power"] = cam.CoolerPower if hasattr(cam, "CoolerPower") else None
        status["sensor_temp"] = cam.CCDTemperature if hasattr(cam, "CCDTemperature") else None
        cam.Connected = False
    except Exception as e:
        print(f"Camera error: {e}")
        status = {"connected": False}
    return status

def get_dome_status():
    pythoncom.CoInitialize()
    device_id = get_device_id("Dome")
    if not device_id:
        print("No dome selected.")
        return {"connected": False}
    dome = win32com.client.Dispatch(device_id)
    status = {}
    try:
        dome.Connected = True
        status["connected"] = True
        status["shutter_status"] = dome.ShutterStatus if hasattr(dome, "ShutterStatus") else None
        dome.Connected = False
    except Exception as e:
        print(f"Dome error: {e}")
        status = {"connected": False}
    return status

def get_filterwheel_status():
    pythoncom.CoInitialize()
    device_id = get_device_id("FilterWheel")
    if not device_id:
        print("No filter wheel selected.")
        return {"connected": False}
    fw = win32com.client.Dispatch(device_id)
    status = {}
    try:
        fw.Connected = True
        status["connected"] = True
        pos = fw.Position if hasattr(fw, "Position") else None
        status["position"] = pos
        if hasattr(fw, "Names"):
            names = fw.Names
            if names and pos is not None and pos < len(names):
                status["filter"] = names[pos]
            else:
                status["filter"] = None
        else:
            status["filter"] = None
        fw.Connected = False
    except Exception as e:
        print(f"FilterWheel error: {e}")
        status = {"connected": False}
    return status

def get_focuser_status():
    pythoncom.CoInitialize()
    device_id = get_device_id("Focuser")
    if not device_id:
        print("No focuser selected.")
        return {"connected": False}
    focuser = win32com.client.Dispatch(device_id)
    status = {}
    try:
        if focuser.Connected:
            status["connected"] = True
            status["position"] = focuser.Position if hasattr(focuser, "Position") else None
            status["is_moving"] = focuser.IsMoving if hasattr(focuser, "IsMoving") else None
            status["temperature"] = focuser.Temperature if hasattr(focuser, "Temperature") else None
        else:
            status["connected"] = False
    except Exception as e:
        print(f"Focuser error: {e}")
        status = {"connected": False}
    return status


def publish(topic, payload, retries=3, delay=2):
    for attempt in range(retries):
        try:
            client = mqtt.Client(protocol=mqtt.MQTTv5)
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.publish(topic, json.dumps(payload))
            print(f"Published to {topic}: {payload}")
            client.disconnect()
            return
        except Exception as e:
            print(f"MQTT publish failed (attempt {attempt+1}/{retries}): {e}")
            time.sleep(delay)
    print(f"Failed to publish to {topic} after {retries} attempts.")

if __name__ == "__main__":
    ra, dec = get_mount_ra_dec()
    if ra is not None and dec is not None:
        publish(MQTT_TOPIC_MOUNT, {"ra": ra, "dec": dec})

    camera_status = get_camera_status()
    publish(MQTT_TOPIC_CAMERA, camera_status)

    dome_status = get_dome_status()
    publish(MQTT_TOPIC_DOME, dome_status)

    filterwheel_status = get_filterwheel_status()
    publish(MQTT_TOPIC_FILTERWHEEL, filterwheel_status)

    focuser_status = get_focuser_status()
    publish(MQTT_TOPIC_FOCUSER, focuser_status)
