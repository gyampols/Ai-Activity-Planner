"""
Utility helper functions for weather, geolocation, and external APIs.
"""
import requests
from datetime import datetime
from urllib.parse import quote


def get_location_from_ip():
    """
    Get location from user's IP address using ipapi.co (free, no API key).
    
    Returns:
        str: City name or None if unable to determine location
    """
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        data = response.json()
        return data.get('city')
    except Exception as e:
        print(f"IP location fetch error: {e}")
        return None


def search_cities(query):
    """
    Search for cities matching the query using Open-Meteo geocoding API.
    
    Args:
        query (str): City name to search for
        
    Returns:
        list: List of dicts containing city information (name, display, latitude, longitude)
    """
    try:
        encoded_query = quote(query)
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_query}&count=10&language=en&format=json"
        response = requests.get(geocode_url, timeout=5)
        data = response.json()
        
        if data.get('results'):
            cities = []
            for result in data['results']:
                city_name = result.get('name', '')
                country = result.get('country', '')
                admin1 = result.get('admin1', '')  # State/Province
                
                # Build display name
                display_parts = [city_name]
                if admin1:
                    display_parts.append(admin1)
                display_parts.append(country)
                
                cities.append({
                    'name': city_name,
                    'display': ', '.join(display_parts),
                    'latitude': result.get('latitude'),
                    'longitude': result.get('longitude')
                })
            return cities
        return []
    except Exception as e:
        print(f"City search error: {e}")
        return []


def get_weather_forecast(location, unit='C'):
    """
    Fetch 7-day weather forecast for the given location using Open-Meteo API.
    
    Args:
        location (str): City name or location
        unit (str): Temperature unit ('C' for Celsius, 'F' for Fahrenheit)
        
    Returns:
        list: List of dicts containing daily forecast data, or None on error
    """
    try:
        # Geocode the location
        encoded_location = quote(location)
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_location}&count=1&language=en&format=json"
        geo_response = requests.get(geocode_url, timeout=5)
        geo_data = geo_response.json()
        
        if not geo_data.get('results'):
            return None
        
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        
        # Get weather forecast with sunrise/sunset
        temp_unit = 'fahrenheit' if unit == 'F' else 'celsius'
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode,sunrise,sunset"
            f"&timezone=auto&forecast_days=7&temperature_unit={temp_unit}"
        )
        weather_response = requests.get(weather_url, timeout=5)
        weather_data = weather_response.json()
        
        # Format the forecast
        forecast = []
        today = datetime.now().date()
        
        for i in range(7):
            date = datetime.fromisoformat(weather_data['daily']['time'][i])
            
            # Parse sunrise and sunset times
            sunrise_str = weather_data['daily']['sunrise'][i]
            sunset_str = weather_data['daily']['sunset'][i]
            sunrise_time = datetime.fromisoformat(sunrise_str).strftime('%I:%M %p')
            sunset_time = datetime.fromisoformat(sunset_str).strftime('%I:%M %p')
            
            forecast.append({
                'date': date.strftime('%A, %B %d'),
                'date_short': date.strftime('%a %m/%d'),
                'temp_max': round(weather_data['daily']['temperature_2m_max'][i]),
                'temp_min': round(weather_data['daily']['temperature_2m_min'][i]),
                'precipitation': weather_data['daily']['precipitation_probability_max'][i],
                'weathercode': weather_data['daily']['weathercode'][i],
                'sunrise': sunrise_time,
                'sunset': sunset_time,
                'is_today': date.date() == today
            })
        
        return forecast
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None
