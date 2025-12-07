"""
AI-powered activity planning routes.
"""
import json
import re
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from openai import OpenAI

from models import db, Activity, Appointment
from utils.helpers import get_weather_forecast
from config import config


planning_bp = Blueprint('planning', __name__)


# Initialize OpenAI client
openai_client = None
if config.OPENAI_API_KEY:
    openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


@planning_bp.route('/plan', methods=['GET', 'POST'])
@login_required
def plan():
    """Display the planning page with activities and weather."""
    from utils.helpers import get_location_from_ip
    
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


@planning_bp.route('/generate_plan', methods=['POST'])
@login_required
def generate_plan():
    """Generate an AI-powered weekly activity plan."""
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
    
    # Build prompt
    prompt = _build_planning_prompt(
        activities, now, current_date, current_time, 
        weather_forecast, readiness_score, sleep_score, extra_info
    )
    
    try:
        if not openai_client:
            # Return mock response if no API key
            return jsonify(_generate_mock_plan(activities, now, weather_forecast))
        
        # Make OpenAI API call
        response = openai_client.chat.completions.create(
            model="gpt-4o",
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
            # Remove markdown code blocks if present
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


def _build_planning_prompt(activities, now, current_date, current_time, 
                           weather_forecast, readiness_score, sleep_score, extra_info):
    """Build the comprehensive prompt for OpenAI."""
    # Prepare activity information
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
    end_date = (now + timedelta(days=6)).date()
    appointments = Appointment.query.filter(
        Appointment.user_id == current_user.id,
        Appointment.date >= now.date(),
        Appointment.date <= end_date
    ).order_by(Appointment.date.asc()).all()
    
    # Generate date keys for the next 7 days
    date_keys = []
    for i in range(7):
        date = now + timedelta(days=i)
        date_key = date.strftime('%Y-%m-%d')
        day_name = date.strftime('%A, %b %d')
        date_keys.append((date_key, day_name))
    
    # Build prompt
    prompt = f"""Current Date & Time: {current_date} at {current_time}

Please create a detailed weekly activity plan for someone who enjoys the following activities:

{chr(10).join(activity_info)}

"""
    
    # Add appointments
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
    
    # Add extra information
    if extra_info:
        prompt += f"\nAdditional Context:\n{extra_info}\n"
    
    # Add weather information
    if weather_forecast:
        temp_unit_display = current_user.temperature_unit or 'C'
        prompt += f"\nWeather forecast for {current_user.location} (with daylight hours):\n"
        for day in weather_forecast:
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
    
    return prompt


def _generate_mock_plan(activities, now, weather_forecast):
    """Generate a mock plan when OpenAI API is not available."""
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
    
    return {'plan': mock_plan, 'structured': True}
