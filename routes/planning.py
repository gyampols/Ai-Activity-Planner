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
        weather_data = get_weather_forecast(current_user.location, temp_unit)
        if weather_data:
            weather_forecast = weather_data.get('forecast')
    
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
        allow_multiple = request_data.get('allow_multiple_activities', False)
    except:
        extra_info = ''
        allow_multiple = False
    
    # Get weather forecast and timezone
    weather_forecast = None
    location_timezone = None
    if current_user.location:
        temp_unit = current_user.temperature_unit or 'C'
        weather_data = get_weather_forecast(current_user.location, temp_unit)
        if weather_data:
            weather_forecast = weather_data.get('forecast')
            location_timezone = weather_data.get('timezone')
    
    # Get current date and time (use location timezone if available)
    if location_timezone:
        try:
            import pytz
            tz = pytz.timezone(location_timezone)
            now = datetime.now(tz)
        except:
            now = datetime.now()
    else:
        now = datetime.now()
    
    current_date = now.strftime('%A, %B %d, %Y')
    current_time = now.strftime('%I:%M %p')
    
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
        weather_forecast, readiness_score, sleep_score, extra_info, allow_multiple
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
                           weather_forecast, readiness_score, sleep_score, extra_info, allow_multiple=False):
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
    
    multiple_activities_instruction = ""
    if allow_multiple:
        multiple_activities_instruction = "13. User wants MULTIPLE activities per day when possible - schedule 2-3 activities per day based on time availability and recovery needs\n"
    else:
        multiple_activities_instruction = "13. Schedule ONE activity per day maximum (unless user has specific appointments/responsibilities)\n"
    
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
{multiple_activities_instruction}

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


@planning_bp.route('/export_to_google_calendar', methods=['POST'])
@login_required
def export_to_google_calendar():
    """Export the generated plan to Google Calendar."""
    if not current_user.google_token:
        return jsonify({'error': 'Google account not connected. Please connect your Google account first.'}), 403
    
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        import pytz
        import json
        
        request_data = request.get_json() or {}
        plan = request_data.get('plan', {})
        
        if not plan:
            return jsonify({'error': 'No plan data provided'}), 400
        
        # Parse the stored credentials
        from google.oauth2.credentials import Credentials
        
        try:
            if current_user.google_token.startswith('{'):
                # New format: JSON with scopes
                credentials_dict = json.loads(current_user.google_token)
                creds = Credentials(
                    token=credentials_dict.get('token'),
                    refresh_token=credentials_dict.get('refresh_token'),
                    token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                    client_id=credentials_dict.get('client_id', config.GOOGLE_CLIENT_ID),
                    client_secret=credentials_dict.get('client_secret', config.GOOGLE_CLIENT_SECRET),
                    scopes=credentials_dict.get('scopes')  # Use the actual scopes from the token
                )
                print(f"[Calendar] Loaded credentials from JSON with scopes: {creds.scopes}")
            else:
                # Old format: just the token string (fallback for existing users)
                creds = Credentials(
                    token=current_user.google_token,
                    refresh_token=current_user.google_refresh_token,
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=config.GOOGLE_CLIENT_ID,
                    client_secret=config.GOOGLE_CLIENT_SECRET,
                    scopes=config.GOOGLE_SCOPES
                )
                print(f"[Calendar] Using legacy token format, assuming scopes: {config.GOOGLE_SCOPES}")
        except Exception as e:
            print(f"[Calendar] Error parsing credentials: {e}")
            # Fallback to old method
            creds = Credentials(
                token=current_user.google_token,
                refresh_token=current_user.google_refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=config.GOOGLE_CLIENT_ID,
                client_secret=config.GOOGLE_CLIENT_SECRET,
                scopes=config.GOOGLE_SCOPES
            )
        
        print(f"[Calendar] Token expired: {creds.expired}, Has refresh token: {bool(creds.refresh_token)}")
        
        # Try to introspect the token to see what scopes it actually has
        try:
            import requests as req
            token_info_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}"
            token_response = req.get(token_info_url, timeout=5)
            if token_response.status_code == 200:
                token_info = token_response.json()
                actual_scopes = token_info.get('scope', '').split()
                print(f"[Calendar] Token info from Google: scopes={actual_scopes}")
                if 'https://www.googleapis.com/auth/calendar.events' not in actual_scopes:
                    print(f"[Calendar] ERROR: Token does NOT have calendar scope! Only has: {actual_scopes}")
            else:
                print(f"[Calendar] Token introspection failed: {token_response.status_code}")
        except Exception as e:
            print(f"[Calendar] Token introspection error: {e}")
        
        # Refresh token if expired (this will also ensure scopes are validated)
        if creds.expired and creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                # Update stored token
                current_user.google_token = creds.token
                db.session.commit()
                print(f"[Calendar] Token refreshed for user {current_user.id}")
            except Exception as e:
                print(f"[Calendar] Token refresh failed: {e}")
                return jsonify({'error': f'Failed to refresh access token. Please reconnect your Google account. Error: {str(e)}'}), 401
        
        # Build Calendar API service
        try:
            service = build('calendar', 'v3', credentials=creds)
            print(f"[Calendar] Service built successfully for user {current_user.id}")
        except Exception as e:
            print(f"[Calendar] Service build failed: {e}")
            return jsonify({'error': f'Failed to connect to Google Calendar API. Please reconnect your Google account. Error: {str(e)}'}), 500
        
        # Get user's timezone (default to UTC if not available)
        timezone = 'UTC'
        try:
            print(f"[Calendar] Fetching calendar info for user {current_user.id}")
            calendar = service.calendars().get(calendarId='primary').execute()
            timezone = calendar.get('timeZone', 'UTC')
            print(f"[Calendar] Got timezone: {timezone}")
        except HttpError as e:
            print(f"[Calendar] HttpError {e.resp.status}: {e}")
            error_details = str(e)
            if e.resp.status == 403:
                # Check if it's specifically a scope issue
                if 'insufficient' in error_details.lower() or 'scope' in error_details.lower():
                    return jsonify({'error': 'Your Google account is connected but does not have calendar permissions. Please disconnect Google from Settings, then reconnect and make sure to approve ALL permissions including calendar access.'}), 403
                return jsonify({'error': 'Calendar access denied. Please disconnect and reconnect your Google account, ensuring you approve calendar access on the Google consent screen.'}), 403
            elif e.resp.status == 401:
                return jsonify({'error': 'Authorization expired. Please disconnect and reconnect your Google account.'}), 401
            print(f"[Calendar] Error getting calendar timezone: {e}")
        except Exception as e:
            print(f"[Calendar] Exception getting calendar timezone: {e}")
        
        tz = pytz.timezone(timezone)
        events_created = 0
        
        # Create events for each day in the plan
        for date_key, day_data in plan.items():
            try:
                # Parse the date
                event_date = datetime.strptime(date_key, '%Y-%m-%d').date()
                activity = day_data.get('activity', '')
                
                # Skip rest days
                if 'rest' in activity.lower():
                    continue
                
                # Create start and end times (default to 9 AM - 10 AM)
                start_datetime = datetime.combine(event_date, datetime.min.time().replace(hour=9))
                end_datetime = datetime.combine(event_date, datetime.min.time().replace(hour=10))
                
                # Localize to user's timezone
                start_datetime = tz.localize(start_datetime)
                end_datetime = tz.localize(end_datetime)
                
                # Build event description
                description = day_data.get('notes', '')
                if day_data.get('weather'):
                    description += f"\n\nWeather: {day_data['weather']}"
                
                # Create the event
                event = {
                    'summary': activity,
                    'description': description,
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': timezone,
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': timezone,
                    },
                    'colorId': '9',  # Blue color for activities
                }
                
                service.events().insert(calendarId='primary', body=event).execute()
                events_created += 1
                
            except Exception as e:
                print(f"Error creating event for {date_key}: {e}")
                continue
        
        if events_created == 0:
            return jsonify({
                'success': False,
                'message': 'No events were created. Your plan may only contain rest days.'
            }), 200
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {events_created} calendar event{"s" if events_created != 1 else ""}!'
        })
        
    except HttpError as e:
        if e.resp.status == 403:
            return jsonify({'error': 'Calendar access denied. Please disconnect and reconnect your Google account to grant calendar permissions.'}), 403
        return jsonify({'error': f'Google Calendar API error: {str(e)}'}), 500
    except Exception as e:
        import traceback
        print(f"Export error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to export to calendar: {str(e)}. Please try reconnecting your Google account.'}), 500
