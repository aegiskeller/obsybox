# Fetch weather data from OpenWeatherMap and publish to MQTT topic obsybox/weather

### NOT USED IN THIS VERSION, USE getweather_mqtt.py INSTEAD

import requests
import json
import time
import paho.mqtt.client as mqtt
from weather_secrets import API_KEY, CITY, MQTT_BROKER, MQTT_PORT

MQTT_TOPIC = "obsybox/weather"

def get_weather(api_key, city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def simplify_weather_data(data):
    return {
        'temperature': data.get('main', {}).get('temp'),
        'humidity': data.get('main', {}).get('humidity'),
        'weather': data.get('weather', [{}])[0].get('description'),
        'wind_speed': data.get('wind', {}).get('speed'),
        'clouds': data.get('clouds', {}).get('all'),
        'timestamp': time.time()
    }

def publish_weather_data(mqtt_client, topic, data):
    payload = json.dumps(data)
    mqtt_client.publish(topic, payload)
    print(f"Published to {topic}: {payload}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
    else:
        print(f"Failed to connect, return code {rc}")

def on_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker. Will attempt to reconnect.")
    while True:
        try:
            client.reconnect()
            print("Reconnected to MQTT broker.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)

def periodic_weather_mqtt(api_key, city, mqtt_client, topic, interval=600):
    while True:
        weather_data = get_weather(api_key, city)
        if weather_data:
            simplified = simplify_weather_data(weather_data)
            publish_weather_data(mqtt_client, topic, simplified)
        else:
            print("Failed to fetch weather data for MQTT publish.")
        time.sleep(interval)

def main():
    api_key = API_KEY
    city = CITY
    mqtt_broker = MQTT_BROKER
    mqtt_port = MQTT_PORT

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_start()

    # Start periodic weather fetch and MQTT publish
    periodic_weather_mqtt(api_key, city, mqtt_client, MQTT_TOPIC, interval=600)

if __name__ == "__main__":
    main()