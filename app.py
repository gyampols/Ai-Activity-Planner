import os
import json
import random
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from models import db, User, Activity
from dotenv import load_dotenv
from openai import OpenAI
import requests
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse, urljoin
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

load_dotenv()

# For Google OAuth in development (allows http://localhost)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///activities.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = None  # No timeout for CSRF tokens

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Set OpenAI API key if available
openai_api_key = os.environ.get('OPENAI_API_KEY')
openai_client = None
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Redirect URIs - use localhost for development
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
GOOGLE_REDIRECT_URI = f"{BASE_URL}/callback/google"
GOOGLE_CONNECT_REDIRECT_URI = f"{BASE_URL}/callback/connect-google"

# Scopes for Google OAuth
GOOGLE_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.sleep.read'
]

# Fitbit OAuth configuration (uses Fitbit API directly)
FITBIT_CLIENT_ID = os.environ.get('FITBIT_CLIENT_ID')
FITBIT_CLIENT_SECRET = os.environ.get('FITBIT_CLIENT_SECRET')
FITBIT_REDIRECT_URI = f"{BASE_URL}/callback/fitbit"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_location_from_ip():
    """Get location from user's IP address using ipapi.co (free, no API key)."""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        data = response.json()
        if data.get('city'):
            return data.get('city')
        return None
    except Exception as e:
        print(f"IP location fetch error: {e}")
        return None

def search_cities(query):
    """Search for cities matching the query."""
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
    """Fetch 7-day weather forecast for the given location."""
    # Using Open-Meteo API (free, no API key required)
    try:
        # First, geocode the location - properly encode the location parameter
        encoded_location = quote(location)
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_location}&count=1&language=en&format=json"
        geo_response = requests.get(geocode_url, timeout=5)
        geo_data = geo_response.json()
        
        if not geo_data.get('results'):
            return None
        
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        
        # Get weather forecast with sunrise/sunset - API returns Celsius by default
        temp_unit = 'fahrenheit' if unit == 'F' else 'celsius'
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode,sunrise,sunset&timezone=auto&forecast_days=7&temperature_unit={temp_unit}"
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
            
            # Convert ISO format to time strings
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

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/log')
@login_required
def log():
    from models import Appointment
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.date.asc()).all()
    return render_template('log.html', activities=activities, appointments=appointments)

@app.route('/add_activity', methods=['POST'])
@login_required
def add_activity():
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    duration = request.form.get('duration', '').strip()
    intensity = request.form.get('intensity', '').strip()
    dependencies = request.form.get('dependencies', '').strip()
    description = request.form.get('description', '').strip()
    preferred_time = request.form.get('preferred_time', '').strip()
    preferred_days = request.form.getlist('preferred_days')  # Get list of checked days
    
    if name:
        # Safely convert duration to integer
        duration_minutes = None
        if duration:
            try:
                duration_minutes = int(duration)
                if duration_minutes < 1:
                    flash('Duration must be a positive number!', 'error')
                    return redirect(url_for('log'))
            except ValueError:
                flash('Duration must be a valid number!', 'error')
                return redirect(url_for('log'))
        
        # Join preferred days with comma
        preferred_days_str = ','.join(preferred_days) if preferred_days else None
        
        activity = Activity(
            user_id=current_user.id,
            name=name[:100],  # Limit length
            location=location[:200] if location else None,
            duration_minutes=duration_minutes,
            intensity=intensity if intensity in ['Low', 'Medium', 'High'] else None,
            dependencies=dependencies[:500] if dependencies else None,
            description=description[:1000] if description else None,
            preferred_time=preferred_time if preferred_time else None,
            preferred_days=preferred_days_str
        )
        db.session.add(activity)
        db.session.commit()
        flash('Activity added successfully!', 'success')
    else:
        flash('Activity name is required!', 'error')
    
    return redirect(url_for('log'))

@app.route('/delete_activity/<int:activity_id>', methods=['POST'])
@login_required
def delete_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.user_id == current_user.id:
        db.session.delete(activity)
        db.session.commit()
        flash('Activity deleted successfully!', 'success')
    else:
        flash('Unauthorized action!', 'error')
    return redirect(url_for('log'))

@app.route('/add_appointment', methods=['POST'])
@login_required
def add_appointment():
    from models import Appointment
    from datetime import datetime as dt
    
    title = request.form.get('title', '').strip()
    appointment_type = request.form.get('appointment_type', '').strip()
    date_str = request.form.get('date', '').strip()
    time_str = request.form.get('time', '').strip()
    duration = request.form.get('duration_minutes', '').strip()
    description = request.form.get('description', '').strip()
    
    if title and date_str:
        # Parse date
        try:
            appointment_date = dt.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format!', 'error')
            return redirect(url_for('log'))
        
        # Parse time if provided
        appointment_time = None
        if time_str:
            try:
                appointment_time = dt.strptime(time_str, '%H:%M').time()
            except ValueError:
                flash('Invalid time format!', 'error')
                return redirect(url_for('log'))
        
        # Parse duration
        duration_minutes = None
        if duration:
            try:
                duration_minutes = int(duration)
                if duration_minutes < 1:
                    flash('Duration must be a positive number!', 'error')
                    return redirect(url_for('log'))
            except ValueError:
                flash('Duration must be a valid number!', 'error')
                return redirect(url_for('log'))
        
        appointment = Appointment(
            user_id=current_user.id,
            title=title[:200],
            appointment_type=appointment_type if appointment_type else 'Other',
            date=appointment_date,
            time=appointment_time,
            duration_minutes=duration_minutes,
            description=description[:1000] if description else None
        )
        db.session.add(appointment)
        db.session.commit()
        flash('Appointment added successfully!', 'success')
    else:
        flash('Title and date are required!', 'error')
    
    return redirect(url_for('log'))

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    from models import Appointment
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.user_id == current_user.id:
        db.session.delete(appointment)
        db.session.commit()
        flash('Appointment deleted successfully!', 'success')
    else:
        flash('Unauthorized action!', 'error')
    return redirect(url_for('log'))

@app.route('/search_cities')
@login_required
def search_cities_route():
    """API endpoint for city autocomplete."""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    cities = search_cities(query)
    return jsonify(cities)

@app.route('/toggle_temperature_unit', methods=['POST'])
@login_required
@csrf.exempt  # AJAX endpoint - CSRF handled via X-CSRFToken header
def toggle_temperature_unit():
    """Toggle between Celsius and Fahrenheit."""
    current_user.temperature_unit = 'F' if current_user.temperature_unit == 'C' else 'C'
    db.session.commit()
    return jsonify({'unit': current_user.temperature_unit})

@app.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            current_user.location = location
            db.session.commit()
    
    # Auto-detect location if user doesn't have one set
    if not current_user.location:
        ip_location = get_location_from_ip()
        if ip_location:
            current_user.location = ip_location
            db.session.commit()
    
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    weather_forecast = None
    if current_user.location:
        temp_unit = current_user.temperature_unit or 'C'
        weather_forecast = get_weather_forecast(current_user.location, temp_unit)
    
    return render_template('plan.html', activities=activities, weather_forecast=weather_forecast)

@app.route('/generate_plan', methods=['POST'])
@login_required
@csrf.exempt  # AJAX endpoint - CSRF handled via same-origin policy
def generate_plan():
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    
    if not activities:
        return jsonify({'error': 'Please add some activities first!'}), 400
    
    # Get extra info from request
    try:
        request_data = request.get_json() or {}
        extra_info = request_data.get('extra_info', '').strip()
    except:
        extra_info = ''
    
    # Get current date and time
    now = datetime.now()
    current_date = now.strftime('%A, %B %d, %Y')
    current_time = now.strftime('%I:%M %p')
    
    # Get weather forecast
    weather_forecast = None
    if current_user.location:
        temp_unit = current_user.temperature_unit or 'C'
        weather_forecast = get_weather_forecast(current_user.location, temp_unit)
    
    # Get readiness scores
    readiness_score = None
    sleep_score = None
    if current_user.fitbit_connected:
        readiness_score = current_user.fitbit_readiness_score
        sleep_score = current_user.fitbit_sleep_score
    elif current_user.oura_connected and current_user.oura_readiness_score:
        readiness_score = current_user.oura_readiness_score
    
    # Prepare activity information for OpenAI
    activity_info = []
    for activity in activities:
        info = f"- {activity.name}"
        if activity.duration_minutes:
            info += f" (Duration: {activity.duration_minutes} min)"
        if activity.intensity:
            info += f" (Intensity: {activity.intensity})"
        if activity.location:
            info += f" (Location: {activity.location})"
        if activity.preferred_time:
            info += f" (Preferred Time: {activity.preferred_time})"
        if activity.preferred_days:
            info += f" (Preferred Days: {activity.preferred_days})"
        if activity.dependencies:
            info += f" (Dependencies: {activity.dependencies})"
        if activity.description:
            info += f" - {activity.description}"
        activity_info.append(info)
    
    # Get appointments for the next 7 days
    from models import Appointment
    end_date = (now + timedelta(days=6)).date()
    appointments = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.date >= now.date(),
        Appointment.date <= end_date
    ).order_by(Appointment.date.asc()).all()
    
    # Build comprehensive prompt
    prompt = f"""Current Date & Time: {current_date} at {current_time}

Please create a detailed weekly activity plan for someone who enjoys the following activities:

{chr(10).join(activity_info)}

"""
    
    # Generate date keys for the next 7 days (needed for prompt)
    date_keys = []
    for i in range(7):
        date = now + timedelta(days=i)
        date_key = date.strftime('%Y-%m-%d')  # e.g., "2025-12-06"
        day_name = date.strftime('%A, %b %d')  # e.g., "Friday, Dec 06"
        date_keys.append((date_key, day_name))
    
    # Add appointments/responsibilities
    if appointments:
        prompt += f"\nScheduled Appointments & Responsibilities:\n"
        for apt in appointments:
            apt_date = apt.date.strftime('%A, %b %d (%Y-%m-%d)')
            apt_info = f"- {apt.title} ({apt.appointment_type}) on {apt_date}"
            if apt.time:
                apt_info += f" at {apt.time.strftime('%I:%M %p')}"
            if apt.duration_minutes:
                apt_info += f" ({apt.duration_minutes} min)"
            if apt.description:
                apt_info += f" - {apt.description}"
            prompt += apt_info + "\n"
        prompt += "\nIMPORTANT: Work activities around these appointments. Do NOT schedule conflicting activities.\n"
    
    # Add extra information from user
    if extra_info:
        prompt += f"\nAdditional Context:\n{extra_info}\n"
    
    # Add weather information
    if weather_forecast:
        prompt += f"\nWeather forecast for {current_user.location} (with daylight hours):\n"
        for day in weather_forecast:
            temp_unit_display = current_user.temperature_unit or 'C'
            prompt += f"- {day['date_short']}: {day['temp_max']}°{temp_unit_display}, Precipitation: {day['precipitation']}%, "
            prompt += f"Sunrise: {day['sunrise']}, Sunset: {day['sunset']}\n"
        prompt += "\nIMPORTANT: Consider sunrise/sunset times for outdoor activities that require daylight. Schedule outdoor activities during daylight hours only.\n"
    
    # Add readiness and sleep scores
    if readiness_score or sleep_score:
        prompt += f"\nToday's Biometric Data (for {date_keys[0][1]} ONLY - do not apply to future days):\n"
        
        if readiness_score:
            prompt += f"- Readiness score: {readiness_score}/100"
            if readiness_score < 60:
                prompt += " (Low - prioritize recovery and lighter activities today)\n"
            elif readiness_score < 80:
                prompt += " (Moderate - balanced activity load today)\n"
            else:
                prompt += " (High - can handle intense activities today)\n"
        
        if sleep_score:
            prompt += f"- Sleep score: {sleep_score}%"
            if sleep_score < 70:
                prompt += " (Poor - extra rest recommended today)\n"
            elif sleep_score < 85:
                prompt += " (Moderate quality)\n"
            else:
                prompt += " (Excellent quality)\n"
        
        prompt += "\nIMPORTANT: These scores are ONLY for today. For future days, plan activities normally based on weather and activity preferences, as we don't have readiness data for those days yet.\n"
    
    prompt += f"""
Create a balanced weekly schedule that:
1. Distributes activities throughout the week based on weather conditions
2. For TODAY ONLY ({date_keys[0][1]}, current time {current_time}): 
   - Adjust intensity based on today's readiness/sleep scores if provided
   - Consider the current time of day ({current_time}) - if it's late in the day, suggest evening-appropriate activities or rest
   - If it's early morning, suggest morning activities; if afternoon, suggest afternoon activities
   - Check if it's before sunset for outdoor activities requiring daylight
3. For FUTURE DAYS: Plan normally based on weather and preferences (no readiness data available yet)
4. Respect activity time preferences (Morning, Afternoon, Evening, Night) when provided
5. Respect preferred days of the week for activities when specified
6. Work around scheduled appointments - DO NOT schedule activities that conflict with appointments
7. Consider sunrise and sunset times - ONLY schedule outdoor activities that require daylight between sunrise and sunset
8. For activities requiring daylight (e.g., outdoor sports, hiking, biking), ensure they're scheduled during daylight hours
9. Indoor activities can be scheduled any time
10. Considers intensity levels to avoid overtraining across the week
11. Takes into account dependencies (weather, equipment, location)
12. Schedules outdoor activities on days with good weather AND sufficient daylight

Please provide a day-by-day plan starting from today in the following JSON format for easy calendar display.
Use the following date keys (these are the actual dates):
"""
    for date_key, day_name in date_keys:
        prompt += f'  "{date_key}": {{"day_name": "{day_name}", "activity": "Activity name or Rest", "notes": "Brief explanation"}}\n'
    
    prompt += "\nReturn only the JSON object with these exact date keys.\n"

    try:
        if not openai_client:
            # Return a mock structured response if no API key
            mock_plan = {}
            
            for i in range(7):
                date = now + timedelta(days=i)
                date_key = date.strftime('%Y-%m-%d')
                day_name = date.strftime('%A, %b %d')
                
                if weather_forecast and i < len(weather_forecast):
                    weather = weather_forecast[i]
                    temp_unit = current_user.temperature_unit or 'C'
                    if weather['precipitation'] > 60:
                        mock_plan[date_key] = {
                            "day_name": day_name,
                            "activity": "Indoor Yoga or Rest",
                            "notes": f"High precipitation ({weather['precipitation']}%). Stay indoors.",
                            "weather": f"{weather['temp_max']}°{temp_unit}, {weather['precipitation']}% rain"
                        }
                    else:
                        activity = activities[i % len(activities)]
                        mock_plan[date_key] = {
                            "day_name": day_name,
                            "activity": activity.name,
                            "notes": f"Good weather for outdoor activities. {activity.intensity or 'Moderate'} intensity.",
                            "weather": f"{weather['temp_max']}°{temp_unit}, {weather['precipitation']}% rain"
                        }
                else:
                    activity = activities[i % len(activities)]
                    mock_plan[date_key] = {
                        "day_name": day_name,
                        "activity": activity.name if i % 3 != 0 else "Rest Day",
                        "notes": "Scheduled based on your activity preferences.",
                        "weather": "No weather data"
                    }
            
            return jsonify({'plan': mock_plan, 'structured': True})
        
        # Make OpenAI API call
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Latest GPT-4 model (GPT-4 Omni)
            messages=[
                {"role": "system", "content": "You are a helpful fitness and activity planning assistant. Always respond with valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        plan_text = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            import json
            import re
            
            # Remove markdown code blocks if present
            # Pattern matches ```json ... ``` or ``` ... ```
            cleaned_text = re.sub(r'^```(?:json)?\s*\n', '', plan_text, flags=re.MULTILINE)
            cleaned_text = re.sub(r'\n```\s*$', '', cleaned_text, flags=re.MULTILINE)
            cleaned_text = cleaned_text.strip()
            
            plan_json = json.loads(cleaned_text)
            return jsonify({'plan': plan_json, 'structured': True})
        except Exception as e:
            print(f"JSON parsing error: {e}")
            print(f"Plan text: {plan_text}")
            # If not JSON, return as text
            return jsonify({'plan': plan_text, 'structured': False})
    
    except Exception as e:
        return jsonify({'error': f'Error generating plan: {str(e)}'}), 500

@app.route('/connect_fitbit', methods=['POST'])
@login_required
def connect_fitbit():
    """Initiate Fitbit OAuth flow."""
    if not FITBIT_CLIENT_ID or not FITBIT_CLIENT_SECRET:
        # Fallback to mock data if Fitbit OAuth not configured
        current_user.fitbit_connected = True
        current_user.fitbit_readiness_score = random.randint(65, 95)
        db.session.commit()
        flash(f'Fitbit connected (Mock data)! Current readiness: {current_user.fitbit_readiness_score}/100', 'success')
        return redirect(url_for('log'))
    
    # Real Fitbit OAuth flow
    import base64
    auth_url = "https://www.fitbit.com/oauth2/authorize"
    scope = "activity heartrate sleep profile"
    
    # Create state token for security
    state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    session['fitbit_state'] = state
    
    params = {
        'response_type': 'code',
        'client_id': FITBIT_CLIENT_ID,
        'redirect_uri': FITBIT_REDIRECT_URI,
        'scope': scope,
        'state': state
    }
    
    auth_request_url = f"{auth_url}?{'&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])}"
    return redirect(auth_request_url)

@app.route('/callback/fitbit')
@login_required
def callback_fitbit():
    """Handle Fitbit OAuth callback."""
    if not FITBIT_CLIENT_ID or not FITBIT_CLIENT_SECRET:
        flash('Fitbit OAuth is not configured.', 'error')
        return redirect(url_for('log'))
    
    # Verify state
    state = session.get('fitbit_state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter.', 'error')
        return redirect(url_for('log'))
    
    code = request.args.get('code')
    if not code:
        flash('Failed to connect Fitbit.', 'error')
        return redirect(url_for('log'))
    
    try:
        # Exchange code for access token
        import base64
        token_url = "https://api.fitbit.com/oauth2/token"
        
        # Fitbit requires HTTP Basic Auth with client_id:client_secret
        credentials = f"{FITBIT_CLIENT_ID}:{FITBIT_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': FITBIT_REDIRECT_URI
        }
        
        response = requests.post(token_url, headers=headers, data=data, timeout=10)
        token_data = response.json()
        
        if 'access_token' in token_data:
            # Store tokens
            current_user.fitbit_token = json.dumps(token_data)
            current_user.fitbit_connected = True
            
            # Fetch user's data from Fitbit API
            access_token = token_data['access_token']
            today = datetime.now().strftime('%Y-%m-%d')
            fitbit_headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get Daily Readiness Score (requires Premium)
            # Note: Readiness Score is only available to Fitbit Premium users
            try:
                readiness_url = f"https://api.fitbit.com/1/user/-/activities/readiness/date/{today}.json"
                readiness_response = requests.get(readiness_url, headers=fitbit_headers, timeout=10)
                
                if readiness_response.status_code == 200:
                    readiness_data = readiness_response.json()
                    # Fitbit returns readiness score directly or in a score field
                    if 'score' in readiness_data:
                        current_user.fitbit_readiness_score = int(readiness_data['score'])
                    elif 'value' in readiness_data:
                        current_user.fitbit_readiness_score = int(readiness_data['value'])
                    else:
                        current_user.fitbit_readiness_score = None
                else:
                    # Readiness not available (not Premium or endpoint not accessible)
                    print(f"Fitbit readiness status: {readiness_response.status_code}")
                    if readiness_response.status_code != 404:
                        print(f"Fitbit readiness response: {readiness_response.text}")
                    current_user.fitbit_readiness_score = None
            except Exception as e:
                print(f"Fitbit readiness fetch error: {e}")
                current_user.fitbit_readiness_score = None
            
            # Get sleep score (available to all users)
            try:
                sleep_url = f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json"
                sleep_response = requests.get(sleep_url, headers=fitbit_headers, timeout=10)
                
                if sleep_response.status_code == 200:
                    sleep_data = sleep_response.json()
                    print(f"Fitbit sleep data: {json.dumps(sleep_data, indent=2)}")
                    
                    # Get sleep score if available
                    if sleep_data.get('sleep') and len(sleep_data['sleep']) > 0:
                        sleep_log = sleep_data['sleep'][0]
                        
                        # Check for overall sleep score first (Fitbit's sleep score 0-100)
                        if 'sleepScore' in sleep_log:
                            current_user.fitbit_sleep_score = int(sleep_log['sleepScore'])
                        elif 'efficiency' in sleep_log:
                            # Fallback to efficiency as a percentage
                            current_user.fitbit_sleep_score = int(sleep_log['efficiency'])
                        else:
                            current_user.fitbit_sleep_score = None
                            print("No sleep score or efficiency found in sleep log")
                        
                        # If readiness score wasn't available, calculate from sleep data
                        if current_user.fitbit_readiness_score is None:
                            sleep_minutes = sleep_data.get('summary', {}).get('totalMinutesAsleep', 0)
                            print(f"Total sleep minutes: {sleep_minutes}")
                            if sleep_minutes > 0:
                                # Calculate readiness based on sleep (7-9 hours optimal)
                                if sleep_minutes >= 420 and sleep_minutes <= 540:  # 7-9 hours
                                    current_user.fitbit_readiness_score = min(100, 85 + (sleep_minutes - 420) // 12)
                                elif sleep_minutes < 420:
                                    current_user.fitbit_readiness_score = max(40, 85 - (420 - sleep_minutes) // 6)
                                else:
                                    current_user.fitbit_readiness_score = max(70, 90 - (sleep_minutes - 540) // 10)
                            else:
                                current_user.fitbit_readiness_score = 75
                    else:
                        print("No sleep data found for today")
                        current_user.fitbit_sleep_score = None
                        if current_user.fitbit_readiness_score is None:
                            current_user.fitbit_readiness_score = 75
                else:
                    print(f"Sleep API status: {sleep_response.status_code}")
                    current_user.fitbit_sleep_score = None
                    if current_user.fitbit_readiness_score is None:
                        current_user.fitbit_readiness_score = 75
            except Exception as e:
                print(f"Fitbit sleep fetch error: {e}")
                import traceback
                traceback.print_exc()
                current_user.fitbit_sleep_score = None
                if current_user.fitbit_readiness_score is None:
                    current_user.fitbit_readiness_score = 75
            
            db.session.commit()
            session.pop('fitbit_state', None)
            
            message = f'Fitbit connected successfully! '
            if current_user.fitbit_readiness_score:
                message += f'Readiness: {current_user.fitbit_readiness_score}/100'
            if current_user.fitbit_sleep_score:
                message += f', Sleep: {current_user.fitbit_sleep_score}%'
            flash(message, 'success')
        else:
            flash('Failed to get Fitbit access token.', 'error')
            
    except Exception as e:
        print(f"Fitbit connection error: {e}")
        flash('Failed to connect Fitbit.', 'error')
    
    return redirect(url_for('log'))

@app.route('/connect_oura', methods=['POST'])
@login_required
def connect_oura():
    current_user.oura_connected = True
    current_user.oura_readiness_score = random.randint(65, 95)  # Mock readiness score
    db.session.commit()
    flash(f'Oura connected successfully! Current readiness: {current_user.oura_readiness_score}/100 (Mock data)', 'success')
    return redirect(url_for('log'))

@app.route('/disconnect_google', methods=['POST'])
@login_required
def disconnect_google():
    """Disconnect Google account from user."""
    if current_user.google_id:
        current_user.google_id = None
        current_user.google_token = None
        current_user.google_refresh_token = None
        db.session.commit()
        flash('Google account disconnected successfully!', 'success')
    else:
        flash('No Google account connected.', 'error')
    return redirect(url_for('log'))

@app.route('/disconnect_fitbit', methods=['POST'])
@login_required
def disconnect_fitbit():
    """Disconnect Fitbit account from user."""
    if current_user.fitbit_connected:
        current_user.fitbit_connected = False
        current_user.fitbit_token = None
        current_user.fitbit_readiness_score = None
        current_user.fitbit_sleep_score = None
        db.session.commit()
        flash('Fitbit account disconnected successfully!', 'success')
    else:
        flash('No Fitbit account connected.', 'error')
    return redirect(url_for('log'))

@app.route('/disconnect_oura', methods=['POST'])
@login_required
def disconnect_oura():
    """Disconnect Oura account from user."""
    if current_user.oura_connected:
        current_user.oura_connected = False
        current_user.oura_readiness_score = None
        db.session.commit()
        flash('Oura account disconnected successfully!', 'success')
    else:
        flash('No Oura account connected.', 'error')
    return redirect(url_for('log'))

def is_safe_url(target):
    """Check if the target URL is safe for redirects."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required!', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate username
        if not username or len(username) < 3 or len(username) > 80:
            flash('Username must be between 3 and 80 characters!', 'error')
            return render_template('signup.html')
        
        if not username.replace('_', '').replace('-', '').isalnum():
            flash('Username can only contain letters, numbers, hyphens, and underscores!', 'error')
            return render_template('signup.html')
        
        # Validate email
        if not email or '@' not in email or len(email) > 120:
            flash('Please provide a valid email address!', 'error')
            return render_template('signup.html')
        
        # Validate password
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('signup.html')
        
        # Check for existing user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'error')
            return render_template('signup.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'error')
            return render_template('signup.html')
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login/google')
def login_google():
    """Initiate Google OAuth login."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured. Please contact the administrator.', 'error')
        return redirect(url_for('login'))
    
    # Create flow instance
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback/google')
def callback_google():
    """Handle Google OAuth callback."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('login'))
    
    # Verify state
    state = session.get('state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter. Please try again.', 'error')
        return redirect(url_for('login'))
    
    try:
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_REDIRECT_URI]
                }
            },
            scopes=GOOGLE_SCOPES,
            state=state,
            redirect_uri=GOOGLE_REDIRECT_URI
        )
        
        # Fetch token
        flow.fetch_token(authorization_response=request.url)
        
        # Get credentials
        credentials = flow.credentials
        
        # Verify token and get user info
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        google_id = idinfo['sub']
        email = idinfo.get('email')
        name = idinfo.get('name', email.split('@')[0])
        
        # Check if user exists
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            # Check if email already exists
            user = User.query.filter_by(email=email).first()
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.google_token = credentials.token
                user.google_refresh_token = credentials.refresh_token
            else:
                # Create new user
                # Generate unique username from email
                base_username = email.split('@')[0]
                username = base_username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User(
                    username=username,
                    email=email,
                    google_id=google_id,
                    google_token=credentials.token,
                    google_refresh_token=credentials.refresh_token
                )
                db.session.add(user)
        else:
            # Update tokens
            user.google_token = credentials.token
            if credentials.refresh_token:
                user.google_refresh_token = credentials.refresh_token
        
        db.session.commit()
        login_user(user)
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Failed to authenticate with Google. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/connect/google')
@login_required
def connect_google():
    """Connect Google account to existing user."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('log'))
    
    # Create flow instance
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_CONNECT_REDIRECT_URI]
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_CONNECT_REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['state'] = state
    session['connect_google'] = True
    return redirect(authorization_url)

@app.route('/callback/connect-google')
def callback_connect_google():
    """Handle Google account connection callback."""
    # Check if user is logged in and has initiated connection
    if not current_user.is_authenticated:
        flash('You must be logged in to connect a Google account.', 'error')
        return redirect(url_for('login'))
    
    if not session.get('connect_google'):
        flash('Invalid request.', 'error')
        return redirect(url_for('log'))
    
    state = session.get('state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter.', 'error')
        return redirect(url_for('log'))
    
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [GOOGLE_CONNECT_REDIRECT_URI]
                }
            },
            scopes=GOOGLE_SCOPES,
            state=state,
            redirect_uri=GOOGLE_CONNECT_REDIRECT_URI
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        google_id = idinfo['sub']
        
        # Check if Google account is already linked to another user
        existing_user = User.query.filter_by(google_id=google_id).first()
        if existing_user and existing_user.id != current_user.id:
            flash('This Google account is already linked to another user.', 'error')
            return redirect(url_for('log'))
        
        # Link to current user
        current_user.google_id = google_id
        current_user.google_token = credentials.token
        current_user.google_refresh_token = credentials.refresh_token
        db.session.commit()
        
        session.pop('connect_google', None)
        flash('Google account connected successfully!', 'success')
        return redirect(url_for('log'))
        
    except Exception as e:
        print(f"Google connection error: {e}")
        flash('Failed to connect Google account.', 'error')
        return redirect(url_for('log'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # WARNING: Debug mode should be disabled in production
    # Set debug=False when deploying to production environments
    app.run(debug=True)
