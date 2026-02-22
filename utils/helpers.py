"""
Utility functions for weather forecasting, geolocation, and external APIs.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

REQUEST_TIMEOUT = 5


def get_location_from_ip() -> Optional[str]:
    """
    Detect user's city from IP address using ipapi.co.

    Returns:
        City name or None if detection fails.
    """
    try:
        response = requests.get('https://ipapi.co/json/', timeout=REQUEST_TIMEOUT)
        return response.json().get('city')
    except Exception:
        return None


def search_cities(query: str) -> List[Dict[str, Any]]:
    """
    Search for cities matching query using Open-Meteo geocoding API.

    Args:
        query: City name to search for.

    Returns:
        List of city dicts with name, display, latitude, longitude.
    """
    try:
        encoded_query = quote(query)
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_query}&count=10&language=en&format=json"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = response.json()

        if not data.get('results'):
            return []

        cities = []
        for result in data['results']:
            city_name = result.get('name', '')
            admin1 = result.get('admin1', '')
            country = result.get('country', '')

            display_parts = [city_name]
            if admin1:
                display_parts.append(admin1)
            display_parts.append(country)

            cities.append({
                'name': city_name,
                'display': ', '.join(display_parts),
                'latitude': result.get('latitude'),
                'longitude': result.get('longitude'),
            })
        return cities
    except Exception:
        return []


def get_weather_forecast(location: str, unit: str = 'C') -> Optional[Dict[str, Any]]:
    """
    Fetch 7-day weather forecast using Open-Meteo API.

    Args:
        location: City name or location string.
        unit: Temperature unit ('C' for Celsius, 'F' for Fahrenheit).

    Returns:
        Dict with forecast data and timezone, or None on error.
    """
    try:
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
        precip_unit_param = 'inch' if unit == 'F' else 'mm'  # Request inches for F, mm for C (will convert to cm)
        # Request daily variables for ground conditions
        # - snowfall_sum: total snowfall for the day
        # - rain_sum: total rain for the day
        # - wind_speed_10m_max: maximum wind speed at 10m height
        # - wind_gusts_10m_max: maximum wind gusts at 10m height
        # Note: snow_depth is NOT a valid daily variable in Open-Meteo
        # Note: For cloud cover, we use hourly data and calculate daily average
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode,sunrise,sunset,snowfall_sum,rain_sum,wind_speed_10m_max,wind_gusts_10m_max"
            f"&hourly=precipitation,rain,snowfall,weathercode,temperature_2m,cloud_cover"
            f"&timezone=auto&forecast_days=7&temperature_unit={temp_unit}&wind_speed_unit=mph&precipitation_unit={precip_unit_param}"
        )
        weather_response = requests.get(weather_url, timeout=5)
        weather_data = weather_response.json()
        
        # Get timezone from weather data
        timezone_str = weather_data.get('timezone', 'UTC')

        # If the 'daily' block is missing, return a safe fallback so the UI
        # and planning routes don't crash. We'll still include timezone and
        # compute next-3-hours summary from hourly when available for today.
        if 'daily' not in weather_data or not weather_data.get('daily'):
            # Derive local 'today' via UTC offset seconds provided by Open-Meteo
            offset_seconds = weather_data.get('utc_offset_seconds', 0)
            now_local = datetime.utcnow() + timedelta(seconds=offset_seconds)
            today = now_local.date()

            hourly = weather_data.get('hourly', {})
            hourly_times = hourly.get('time', [])
            hourly_dt = []
            for t in hourly_times:
                try:
                    hourly_dt.append(datetime.fromisoformat(t.replace('Z', '+00:00')))
                except ValueError:
                    try:
                        hourly_dt.append(datetime.fromisoformat(t))
                    except Exception:
                        continue

            next3_precip = None
            next3_rain = None
            next3_snow = None
            precip_unit_fallback = 'in' if unit == 'F' else 'cm'
            if hourly_dt:
                end = now_local + timedelta(hours=3)
                total_precip = 0.0
                total_rain = 0.0
                total_snow = 0.0
                for idx, hdt in enumerate(hourly_dt):
                    if now_local <= hdt <= end:
                        total_precip += float(hourly.get('precipitation', [0]*len(hourly_dt))[idx] or 0)
                        total_rain += float(hourly.get('rain', [0]*len(hourly_dt))[idx] or 0)
                        total_snow += float(hourly.get('snowfall', [0]*len(hourly_dt))[idx] or 0)
                # Convert based on what the API returned (fallback section)
                # API returns: inches if F requested, mm if C requested
                if unit == 'F':
                    # API returned in inches - use directly
                    next3_precip = round(total_precip, 2)
                    next3_rain = round(total_rain, 2)
                    next3_snow = round(total_snow, 2)
                else:
                    # API returned in mm
                    next3_precip = round(total_precip * 0.1, 2)  # mm to cm
                    next3_rain = round(total_rain * 0.1, 2)  # mm to cm
                    next3_snow = round(total_snow, 2)  # mm = cm for snow

            # Provide a minimal single-day entry for today with only next-3h info
            fallback_forecast = []
            fallback_forecast.append({
                'date': today.strftime('%A, %B %d'),
                'date_short': today.strftime('%a %m/%d'),
                'temp_max': None,
                'temp_min': None,
                'precipitation': None,
                'weathercode': None,
                'sunrise': None,
                'sunset': None,
                'is_today': True,
                'snowfall_sum': None,
                'rain_sum': None,
                'precip_unit': precip_unit_fallback if hourly_dt else 'cm',
                'is_wet_ground': None,
                'is_snowy_ground': None,
                'wind_speed': None,
                'wind_gusts': None,
                'is_windy': False,
                'cloud_cover': None,
                'next3_precip': next3_precip,
                'next3_rain': next3_rain,
                'next3_snow': next3_snow
            })

            return {'forecast': fallback_forecast, 'timezone': timezone_str}
        
        # Format the forecast
        forecast = []
        # Derive local 'today' via UTC offset seconds provided by Open-Meteo
        offset_seconds = weather_data.get('utc_offset_seconds', 0)
        now_local = datetime.utcnow() + timedelta(seconds=offset_seconds)
        today = now_local.date()

        # Build an index for hourly times for quick next-3-hours summary
        hourly = weather_data.get('hourly', {})
        hourly_times = hourly.get('time', [])
        # Convert hourly timestamps
        hourly_dt = []
        # Robust ISO8601 parsing: handle 'Z' and timezone offsets
        for t in hourly_times:
            try:
                dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                hourly_dt.append(dt)
            except ValueError:
                # Fallback: try without replacement
                try:
                    dt = datetime.fromisoformat(t)
                    hourly_dt.append(dt)
                except Exception:
                    continue
        
        for i in range(7):
            # fromisoformat returns a datetime, extract just the date
            date_str = weather_data['daily']['time'][i]
            date = datetime.fromisoformat(date_str).date()
            
            # Parse sunrise and sunset times
            sunrise_str = weather_data['daily']['sunrise'][i]
            sunset_str = weather_data['daily']['sunset'][i]
            sunrise_time = datetime.fromisoformat(sunrise_str.replace('Z', '+00:00')).strftime('%I:%M %p')
            sunset_time = datetime.fromisoformat(sunset_str.replace('Z', '+00:00')).strftime('%I:%M %p')
            
            # Convert date back to datetime for strftime
            date_dt = datetime.combine(date, datetime.min.time())
            
            # Determine simple surface condition flags
            weathercode = weather_data['daily']['weathercode'][i]
            precipitation_prob = weather_data['daily']['precipitation_probability_max'][i]
            snowfall_sum_raw = weather_data['daily'].get('snowfall_sum', [0]*7)[i] or 0
            rain_sum_raw = weather_data['daily'].get('rain_sum', [0]*7)[i] or 0
            
            # Convert based on what the API returned
            # API returns: inches if F requested, mm if C requested
            if unit == 'F':
                # API returned in inches - use directly
                snowfall_sum = round(snowfall_sum_raw, 2)
                rain_sum = round(rain_sum_raw, 2)
                precip_unit = 'in'
            else:
                # API returned in mm, use as-is (mm water equiv ≈ cm snow depth)
                snowfall_sum = round(snowfall_sum_raw, 2)  # mm water equiv = cm snow depth
                rain_sum = round(rain_sum_raw * 0.1, 2)  # mm to cm
                precip_unit = 'cm'
            
            # Wind data (mph)
            wind_speed = weather_data['daily'].get('wind_speed_10m_max', [0]*7)[i] or 0
            wind_gusts = weather_data['daily'].get('wind_gusts_10m_max', [0]*7)[i] or 0
            # Consider windy if sustained wind >= 15 mph or gusts >= 25 mph
            is_windy = wind_speed >= 15 or wind_gusts >= 25

            # Open-Meteo weathercode classification: 71-77 snow, 85-86 snow showers
            is_snow_code = int(weathercode) in {71, 73, 75, 77, 85, 86}
            is_wet = (precipitation_prob is not None and precipitation_prob >= 40) or (rain_sum and rain_sum > 0)
            is_snowy_ground = is_snow_code or (snowfall_sum and snowfall_sum > 0)

            # Compute next 3 hours precipitation summary for today's date only
            next3_precip = None
            next3_rain = None
            next3_snow = None
            if date == today and hourly_dt:
                now_loc = now_local
                end = now_loc + timedelta(hours=3)
                total_precip = 0.0
                total_rain = 0.0
                total_snow = 0.0
                for idx, hdt in enumerate(hourly_dt):
                    if now_loc <= hdt <= end:
                        total_precip += float(hourly.get('precipitation', [0]*len(hourly_dt))[idx] or 0)
                        total_rain += float(hourly.get('rain', [0]*len(hourly_dt))[idx] or 0)
                        total_snow += float(hourly.get('snowfall', [0]*len(hourly_dt))[idx] or 0)
                # Convert based on what the API returned (today section)
                # API returns: inches if F requested, mm if C requested
                if unit == 'F':
                    # API returned in inches - use directly
                    next3_precip = round(total_precip, 2)
                    next3_rain = round(total_rain, 2)
                    next3_snow = round(total_snow, 2)
                else:
                    # API returned in mm
                    next3_precip = round(total_precip * 0.1, 2)  # mm to cm
                    next3_rain = round(total_rain * 0.1, 2)  # mm to cm
                    next3_snow = round(total_snow, 2)  # mm = cm for snow

            # Calculate average cloud cover for this day from hourly data
            cloud_cover_avg = None
            hourly_cloud = hourly.get('cloud_cover', [])
            if hourly_cloud and hourly_dt:
                # Get cloud cover values for hours in this day
                day_cloud_values = []
                for idx, hdt in enumerate(hourly_dt):
                    if hdt.date() == date and idx < len(hourly_cloud):
                        val = hourly_cloud[idx]
                        if val is not None:
                            day_cloud_values.append(val)
                if day_cloud_values:
                    cloud_cover_avg = round(sum(day_cloud_values) / len(day_cloud_values))

            forecast.append({
                'date': date_dt.strftime('%A, %B %d'),
                'date_short': date_dt.strftime('%a %m/%d'),
                'temp_max': round(weather_data['daily']['temperature_2m_max'][i]),
                'temp_min': round(weather_data['daily']['temperature_2m_min'][i]),
                'precipitation': precipitation_prob,
                'weathercode': weathercode,
                'sunrise': sunrise_time,
                'sunset': sunset_time,
                'is_today': date == today,
                # Extended fields used by planning logic/UI
                'snowfall_sum': snowfall_sum,
                'rain_sum': rain_sum,
                'precip_unit': precip_unit,
                'is_wet_ground': bool(is_wet),
                'is_snowy_ground': bool(is_snowy_ground),
                # Wind data (mph)
                'wind_speed': round(wind_speed),
                'wind_gusts': round(wind_gusts),
                'is_windy': bool(is_windy),
                # Cloud cover (%)
                'cloud_cover': cloud_cover_avg,
                # Hourly next-3-hours summary (in or cm)
                'next3_precip': next3_precip,
                'next3_rain': next3_rain,
                'next3_snow': next3_snow
            })
        
        # Return both forecast and timezone
        return {'forecast': forecast, 'timezone': timezone_str}
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None


def get_timezone_for_location(location: str) -> str:
    """Resolve IANA timezone for a location via Open-Meteo geocoding/forecast.

    Returns a timezone string like "America/New_York" or 'UTC' on failure.
    """
    try:
        encoded_location = quote(location)
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_location}&count=1&language=en&format=json"
        geo_response = requests.get(geocode_url, timeout=5)
        geo_data = geo_response.json()
        if not geo_data.get('results'):
            return 'UTC'
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&timezone=auto"
        resp = requests.get(url, timeout=5)
        tz = resp.json().get('timezone')
        return tz or 'UTC'
    except Exception:
        return 'UTC'
