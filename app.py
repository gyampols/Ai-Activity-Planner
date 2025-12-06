import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Activity
from dotenv import load_dotenv
import openai
import requests
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///activities.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Set OpenAI API key if available
openai_api_key = os.environ.get('OPENAI_API_KEY')
if openai_api_key:
    openai.api_key = openai_api_key

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_weather_forecast(location):
    """Fetch 7-day weather forecast for the given location."""
    # Using Open-Meteo API (free, no API key required)
    try:
        # First, geocode the location
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geo_response = requests.get(geocode_url, timeout=5)
        geo_data = geo_response.json()
        
        if not geo_data.get('results'):
            return None
        
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        
        # Get weather forecast
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode&timezone=auto&forecast_days=7"
        weather_response = requests.get(weather_url, timeout=5)
        weather_data = weather_response.json()
        
        # Format the forecast
        forecast = []
        for i in range(7):
            date = datetime.fromisoformat(weather_data['daily']['time'][i])
            forecast.append({
                'date': date.strftime('%A, %B %d'),
                'date_short': date.strftime('%a %m/%d'),
                'temp_max': round(weather_data['daily']['temperature_2m_max'][i]),
                'temp_min': round(weather_data['daily']['temperature_2m_min'][i]),
                'precipitation': weather_data['daily']['precipitation_probability_max'][i],
                'weathercode': weather_data['daily']['weathercode'][i]
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
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    return render_template('log.html', activities=activities)

@app.route('/add_activity', methods=['POST'])
@login_required
def add_activity():
    name = request.form.get('name')
    location = request.form.get('location')
    duration = request.form.get('duration')
    intensity = request.form.get('intensity')
    dependencies = request.form.get('dependencies')
    description = request.form.get('description')
    
    if name:
        activity = Activity(
            user_id=current_user.id,
            name=name,
            location=location,
            duration_minutes=int(duration) if duration else None,
            intensity=intensity,
            dependencies=dependencies,
            description=description
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

@app.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            current_user.location = location
            db.session.commit()
    
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    weather_forecast = None
    if current_user.location:
        weather_forecast = get_weather_forecast(current_user.location)
    
    return render_template('plan.html', activities=activities, weather_forecast=weather_forecast)

@app.route('/generate_plan', methods=['POST'])
@login_required
def generate_plan():
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    
    if not activities:
        return jsonify({'error': 'Please add some activities first!'}), 400
    
    # Get weather forecast
    weather_forecast = None
    if current_user.location:
        weather_forecast = get_weather_forecast(current_user.location)
    
    # Get readiness scores (mock data for now)
    readiness_score = None
    if current_user.fitbit_connected and current_user.fitbit_readiness_score:
        readiness_score = current_user.fitbit_readiness_score
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
        if activity.dependencies:
            info += f" (Dependencies: {activity.dependencies})"
        if activity.description:
            info += f" - {activity.description}"
        activity_info.append(info)
    
    # Build comprehensive prompt
    prompt = f"""Please create a detailed weekly activity plan for someone who enjoys the following activities:

{chr(10).join(activity_info)}

"""
    
    # Add weather information
    if weather_forecast:
        prompt += f"\nWeather forecast for {current_user.location}:\n"
        for day in weather_forecast:
            prompt += f"- {day['date_short']}: {day['temp_max']}°C, Precipitation: {day['precipitation']}%\n"
    
    # Add readiness score
    if readiness_score:
        prompt += f"\nCurrent readiness score: {readiness_score}/100\n"
        if readiness_score < 60:
            prompt += "(Low readiness - prioritize recovery and lighter activities)\n"
        elif readiness_score < 80:
            prompt += "(Moderate readiness - balanced activity load)\n"
        else:
            prompt += "(High readiness - can handle intense activities)\n"
    
    prompt += """
Create a balanced weekly schedule that:
1. Distributes activities throughout the week based on weather conditions
2. Allows for proper rest and recovery based on readiness scores
3. Considers intensity levels to avoid overtraining
4. Takes into account dependencies (weather, equipment, location)
5. Schedules outdoor activities on days with good weather
6. Adjusts intensity based on readiness scores

Please provide a day-by-day plan in the following JSON format for easy calendar display:
{
  "Monday": {"activity": "Activity name or Rest", "notes": "Brief explanation"},
  "Tuesday": {"activity": "Activity name or Rest", "notes": "Brief explanation"},
  ...
}
"""

    try:
        if not openai_api_key:
            # Return a mock structured response if no API key
            today = datetime.now()
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            mock_plan = {}
            
            for i, day in enumerate(days):
                date = today + timedelta(days=i)
                if weather_forecast and i < len(weather_forecast):
                    weather = weather_forecast[i]
                    if weather['precipitation'] > 60:
                        mock_plan[day] = {
                            "activity": "Indoor Yoga or Rest",
                            "notes": f"High precipitation ({weather['precipitation']}%). Stay indoors.",
                            "weather": f"{weather['temp_max']}°C, {weather['precipitation']}% rain"
                        }
                    else:
                        activity = activities[i % len(activities)]
                        mock_plan[day] = {
                            "activity": activity.name,
                            "notes": f"Good weather for outdoor activities. {activity.intensity} intensity.",
                            "weather": f"{weather['temp_max']}°C, {weather['precipitation']}% rain"
                        }
                else:
                    activity = activities[i % len(activities)]
                    mock_plan[day] = {
                        "activity": activity.name if i % 3 != 0 else "Rest Day",
                        "notes": "Scheduled based on your activity preferences.",
                        "weather": "No weather data"
                    }
            
            return jsonify({'plan': mock_plan, 'structured': True})
        
        # Make OpenAI API call
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
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
            plan_json = json.loads(plan_text)
            return jsonify({'plan': plan_json, 'structured': True})
        except:
            # If not JSON, return as text
            return jsonify({'plan': plan_text, 'structured': False})
    
    except Exception as e:
        return jsonify({'error': f'Error generating plan: {str(e)}'}), 500

@app.route('/connect_fitbit', methods=['POST'])
@login_required
def connect_fitbit():
    import random
    current_user.fitbit_connected = True
    current_user.fitbit_readiness_score = random.randint(65, 95)  # Mock readiness score
    db.session.commit()
    flash(f'Fitbit connected successfully! Current readiness: {current_user.fitbit_readiness_score}/100 (Mock data)', 'success')
    return redirect(url_for('log'))

@app.route('/connect_oura', methods=['POST'])
@login_required
def connect_oura():
    import random
    current_user.oura_connected = True
    current_user.oura_readiness_score = random.randint(65, 95)  # Mock readiness score
    db.session.commit()
    flash(f'Oura connected successfully! Current readiness: {current_user.oura_readiness_score}/100 (Mock data)', 'success')
    return redirect(url_for('log'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('signup.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'error')
            return render_template('signup.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'error')
            return render_template('signup.html')
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
