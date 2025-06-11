# here we scrape the weather data from openweathermap.org
# we store this data and then serve it via a webserver
# ArduSafeMon_R4wifi_weather then reads this data
import requests
import json
import time
import os
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
def main():
    api_key = "f0a965789e5e7a3ec34b14d4ad4f2110"
    city = "Canberra"
    weather_data = get_weather(api_key, city)
    if weather_data:
        save_weather_data(weather_data)
    else:
        print("Failed to retrieve weather data.")
if __name__ == "__main__":
    main()
    # Load and print the weather data
    data = load_weather_data()
    if data:
        print(json.dumps(data, indent=4))
    else:
        print("No weather data available.")