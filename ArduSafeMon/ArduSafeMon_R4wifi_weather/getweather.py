# here we scrape the weather data from openweathermap.org
# we store this data and then serve it via a webserver
# ArduSafeMon_R4wifi_weather then reads this data
# flak app on http://192.168.1.3:8080/weather
import requests
import json
import time
import os
import threading

def get_weather(api_key, city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

def save_weather_data(data, filename='weather.json'):
    # here we only keep some of the weather data
    simplified_data = {
        'temperature': data.get('main', {}).get('temp'),
        'humidity': data.get('main', {}).get('humidity'),
        'weather': data.get('weather', [{}])[0].get('description'),
        'wind_speed': data.get('wind', {}).get('speed'),
        'clouds': data.get('clouds', {}).get('all'),
        'timestamp': time.time()
    }
    with open(filename, 'w') as file:
        json.dump(simplified_data, file, indent=4)

def load_weather_data(filename='weather.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            data = json.load(file)
        return data
    else:
        print(f"No weather data file found: {filename}")
        return None 

def periodic_weather_update(api_key, city, interval=600):
    while True:
        weather_data = get_weather(api_key, city)
        if weather_data:
            save_weather_data(weather_data)
            print("Weather data updated.")
        else:
            print("Failed to update weather data.")
        time.sleep(interval)

def main():
    api_key = <your api>
    city = <your city>
    weather_data = get_weather(api_key, city)
    if weather_data:
        save_weather_data(weather_data)
    else:
        print("Failed to retrieve weather data.")

if __name__ == "__main__":
    api_key = <your api key>
    city = <your city>

    # Start periodic weather update in a background thread
    updater = threading.Thread(target=periodic_weather_update, args=(api_key, city), daemon=True)
    updater.start()

    # Load and print the weather data
    data = load_weather_data()
    if data:
        print(json.dumps(data, indent=4))
    else:
        print("No weather data available.")

    # --- Flask endpoint for serving weather data ---
    try:
        from flask import Flask, jsonify
        app = Flask(__name__)

        @app.route('/weather')
        def serve_weather():
            data = load_weather_data()
            if data:
                return jsonify(data)
            else:
                return jsonify({'error': 'No weather data available'}), 404

        print("Starting Flask server on http://0.0.0.0:8080/weather")
        app.run(host='0.0.0.0', port=8080)
    except ImportError:
        print("Flask is not installed. Run 'pip install flask' to enable the web endpoint.")
