import sys
import json
import pythoncom
import win32com.client
import paho.mqtt.client as mqtt

sys.path.append(r"C:\Program Files (x86)\Common Files\ASCOM\Platform")

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_MOUNT = "obsybox/telescope/position"
MQTT_TOPIC_CAMERA = "obsybox/camera/status"
MQTT_TOPIC_DOME = "obsybox/dome/status"
MQTT_TOPIC_FILTERWHEEL = "obsybox/filterwheel/status"
MQTT_TOPIC_FOCUSER = "obsybox/focuser/status"
MQTT_TOPIC_GUIDER = "obsybox/guider/status"
MQTT_TOPIC_SAFETYMON = "obsybox/safetymonitor/status"

def get_mount_ra_dec():
    pythoncom.CoInitialize()
    telescope = win32com.client.Dispatch("ASCOM.Utilities.Chooser").Choose("Telescope")
    if not telescope:
        print("No telescope selected.")
        return None, None
    scope = win32com.client.Dispatch(telescope)
    if not scope.Connected:
        scope.Connected = True
    ra = scope.RightAscension
    dec = scope.Declination
    scope.Connected = False
    return ra, dec

def get_camera_status():
    pythoncom.CoInitialize()
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = "Camera"
    camera_id = chooser.Choose(None)
    if not camera_id:
        print("No camera selected.")
        return {"connected": False}
    cam = win32com.client.Dispatch(camera_id)
    status = {}
    try:
        cam.Connected = True
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
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = "Dome"
    dome_id = chooser.Choose(None)
    if not dome_id:
        print("No dome selected.")
        return {"connected": False}
    dome = win32com.client.Dispatch(dome_id)
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
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = "FilterWheel"
    fw_id = chooser.Choose(None)
    if not fw_id:
        print("No filter wheel selected.")
        return {"connected": False}
    fw = win32com.client.Dispatch(fw_id)
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
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = "Focuser"
    focuser_id = chooser.Choose(None)
    if not focuser_id:
        print("No focuser selected.")
        return {"connected": False}
    focuser = win32com.client.Dispatch(focuser_id)
    status = {}
    try:
        focuser.Connected = True
        status["connected"] = True
        status["position"] = focuser.Position if hasattr(focuser, "Position") else None
        status["temperature"] = focuser.Temperature if hasattr(focuser, "Temperature") else None
        focuser.Connected = False
    except Exception as e:
        print(f"Focuser error: {e}")
        status = {"connected": False}
    return status

def get_guider_status():
    pythoncom.CoInitialize()
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = "Video"
    guider_id = chooser.Choose(None)
    if not guider_id:
        print("No guider selected.")
        return {"connected": False}
    guider = win32com.client.Dispatch(guider_id)
    status = {}
    try:
        guider.Connected = True
        status["connected"] = True
        status["state"] = getattr(guider, "State", None)
        guider.Connected = False
    except Exception as e:
        print(f"Guider error: {e}")
        status = {"connected": False}
    return status

def get_safetymonitor_status():
    pythoncom.CoInitialize()
    chooser = win32com.client.Dispatch("ASCOM.Utilities.Chooser")
    chooser.DeviceType = "SafetyMonitor"
    safemon_id = chooser.Choose(None)
    if not safemon_id:
        print("No safety monitor selected.")
        return {"connected": False}
    safemon = win32com.client.Dispatch(safemon_id)
    status = {}
    try:
        safemon.Connected = True
        status["connected"] = True
        status["is_safe"] = safemon.IsSafe if hasattr(safemon, "IsSafe") else None
        safemon.Connected = False
    except Exception as e:
        print(f"SafetyMonitor error: {e}")
        status = {"connected": False}
    return status

def publish(topic, payload):
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.publish(topic, json.dumps(payload))
    print(f"Published to {topic}: {payload}")
    client.disconnect()

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

    guider_status = get_guider_status()
    publish(MQTT_TOPIC_GUIDER, guider_status)

    safemon_status = get_safetymonitor_status()
    publish(MQTT_TOPIC_SAFETYMON, safemon_status)