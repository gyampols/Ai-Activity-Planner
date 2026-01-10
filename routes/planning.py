"""
AI-powered activity planning routes using OpenAI GPT.
"""
import json
import re
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from openai import OpenAI

from config import config
from models import db, Activity, Appointment
from utils.helpers import get_weather_forecast

planning_bp = Blueprint('planning', __name__)

openai_client = OpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None


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
    
    # Load persisted schedule if available
    last_schedule = None
    last_schedule_date = None
    if current_user.last_generated_schedule:
        try:
            last_schedule = json.loads(current_user.last_generated_schedule)
            last_schedule_date = current_user.last_schedule_date.isoformat() if current_user.last_schedule_date else None
        except (json.JSONDecodeError, TypeError):
            last_schedule = None
    
    return render_template('plan.html', 
                           activities=activities, 
                           weather_forecast=weather_forecast,
                           last_schedule=last_schedule,
                           last_schedule_date=last_schedule_date,
                           last_completed_activity=current_user.last_completed_activity or '',
                           current_injuries=current_user.current_injuries or '',
                           additional_information=current_user.additional_information or '')


@planning_bp.route('/debug/weather')
@login_required
def debug_weather():
    """Return raw weather inputs used by the planner to help align with phone apps."""
    if not current_user.location:
        return jsonify({'error': 'No location set'}), 400
    temp_unit = current_user.temperature_unit or 'C'
    data = get_weather_forecast(current_user.location, temp_unit)
    return jsonify(data or {'error': 'weather fetch failed'})


@planning_bp.route('/update_manual_scores', methods=['POST'])
@login_required
def update_manual_scores():
    """Update user's manual readiness and sleep scores."""
    try:
        data = request.get_json()
        readiness_score = data.get('readiness_score')
        sleep_score = data.get('sleep_score')
        
        # Validate scores
        if readiness_score is not None:
            if not (0 <= readiness_score <= 100):
                return jsonify({'error': 'Readiness score must be between 0 and 100'}), 400
            current_user.manual_readiness_score = readiness_score
        
        if sleep_score is not None:
            if not (0 <= sleep_score <= 100):
                return jsonify({'error': 'Sleep score must be between 0 and 100'}), 400
            current_user.manual_sleep_score = sleep_score
        
        # Update the date
        current_user.manual_score_date = datetime.now().date()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scores updated successfully',
            'readiness_score': current_user.manual_readiness_score,
            'sleep_score': current_user.manual_sleep_score
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update scores: {str(e)}'}), 500


@planning_bp.route('/generate_plan', methods=['POST'])
@login_required
def generate_plan():
    """Generate an AI-powered weekly activity plan."""
    from datetime import date
    
    # Check subscription tier limits
    today = date.today()
    
    # Reset weekly counter if needed (resets every Monday)
    if current_user.plan_generation_reset_date is None or current_user.plan_generation_reset_date < today:
        # Find next Monday (or today if it's Monday)
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0 and current_user.plan_generation_reset_date != today:
            days_until_monday = 7
        next_reset = today + timedelta(days=days_until_monday if days_until_monday > 0 else 7)
        current_user.plan_generation_reset_date = next_reset
        current_user.plan_generations_count = 0
        db.session.commit()
    
    # Check tier-based limits
    tier_limits = {
        'free_tier': 3,
        'paid_tier': float('inf'),  # Unlimited for paid users
        'admin': float('inf')  # Unlimited
    }
    
    user_tier = current_user.subscription_tier or 'free_tier'
    limit = tier_limits.get(user_tier, 3)
    
    if current_user.plan_generations_count >= limit:
        days_until_reset = (current_user.plan_generation_reset_date - today).days
        return jsonify({
            'error': f'You have reached your weekly limit of {int(limit)} plan generations. Your limit resets in {days_until_reset} day(s). Consider upgrading to paid tier for unlimited generations!',
            'limit_reached': True,
            'current_tier': user_tier,
            'generations_used': current_user.plan_generations_count,
            'limit': int(limit) if limit != float('inf') else 'unlimited',
            'reset_date': current_user.plan_generation_reset_date.isoformat()
        }), 429
    
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    
    if not activities:
        return jsonify({'error': 'Please add some activities first!'}), 400
    
    # Get extra info from request
    try:
        request_data = request.get_json() or {}
        extra_info = request_data.get('extra_info', '').strip()
        last_activity = request_data.get('last_activity', '').strip()
        injuries_pains = request_data.get('injuries_pains', '').strip()
        allow_multiple = request_data.get('allow_multiple_activities', False)
        excluded_activity_ids = request_data.get('excluded_activity_ids', [])
        
        # Save these values to user profile for persistence
        current_user.last_completed_activity = last_activity if last_activity else None
        current_user.current_injuries = injuries_pains if injuries_pains else None
        current_user.additional_information = extra_info if extra_info else None
        db.session.commit()
        
    except (TypeError, AttributeError, KeyError):
        extra_info = ''
        injuries_pains = ''
        allow_multiple = False
        excluded_activity_ids = []
    
    # Filter out excluded activities
    if excluded_activity_ids:
        activities = [a for a in activities if a.id not in excluded_activity_ids]
        if not activities:
            return jsonify({'error': 'Please include at least one activity in your plan!'}), 400
    
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
        except (ImportError, pytz.exceptions.UnknownTimeZoneError):
            now = datetime.now()
    else:
        now = datetime.now()
    
    current_date = now.strftime('%A, %B %d, %Y')
    current_time = now.strftime('%I:%M %p')
    
    # Get readiness scores (prioritize tracker data, fallback to manual)
    readiness_score = None
    sleep_score = None
    
    if current_user.fitbit_connected:
        readiness_score = current_user.fitbit_readiness_score
        sleep_score = current_user.fitbit_sleep_score
    elif current_user.oura_connected and current_user.oura_readiness_score:
        readiness_score = current_user.oura_readiness_score
    
    # Fallback to manual scores if no tracker data available
    if readiness_score is None and current_user.manual_readiness_score is not None:
        # Check if manual scores are from today
        if current_user.manual_score_date and current_user.manual_score_date >= now.date():
            readiness_score = current_user.manual_readiness_score
            sleep_score = current_user.manual_sleep_score
    
    # Build prompt
    prompt = _build_planning_prompt(
        activities, now, current_date, current_time, 
        weather_forecast, readiness_score, sleep_score, extra_info, last_activity, allow_multiple, injuries_pains
    )
    
    try:
        if not openai_client:
            # Return mock response if no API key
            return jsonify(_generate_mock_plan(activities, now, weather_forecast))
        
        # Make OpenAI API call with optimized parameters
        # Use gpt-4o for reliable JSON generation
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": """You are an expert fitness and wellness planning assistant specializing in personalized activity scheduling.

CORE COMPETENCIES:
- Exercise science and recovery optimization
- Weather-based activity planning
- Time management and scheduling logic
- Biometric data interpretation (readiness/sleep scores)

OUTPUT REQUIREMENTS:
- Always return pure JSON (no markdown, no code blocks, no explanations)
- Follow exact date key format provided in prompt
- Apply logical reasoning for activity timing and intensity
- Consider all constraints (appointments, weather, daylight, fitness levels)

DECISION PRINCIPLES:
- Safety first (weather conditions, recovery needs, daylight requirements)
- Respect user preferences (time/day preferences, activity types)
- Balance variety with consistency
- Optimize for long-term adherence and enjoyment
- consider the users preferences and constraints when generating the plan"""
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        
        plan_text = response.choices[0].message.content
        
        # Handle empty response
        if not plan_text or not plan_text.strip():
            print("OpenAI returned empty content")
            return jsonify({'error': 'AI returned empty response. Please try again.'}), 500
        
        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            cleaned_text = re.sub(r'^```(?:json)?\s*\n', '', plan_text, flags=re.MULTILINE)
            cleaned_text = re.sub(r'\n```\s*$', '', cleaned_text, flags=re.MULTILINE)
            cleaned_text = cleaned_text.strip()
            
            plan_json = json.loads(cleaned_text)
            
            # Increment generation counter on successful plan creation
            current_user.plan_generations_count += 1
            
            # Save the generated schedule for persistence
            current_user.last_generated_schedule = json.dumps(plan_json)
            current_user.last_schedule_date = datetime.now()
            db.session.commit()
            
            return jsonify({'plan': plan_json, 'structured': True})
        except Exception as e:
            print(f"JSON parsing error: {e}")
            print(f"Plan text: {plan_text}")
            # If not JSON, return as text
            # Still increment counter as plan was generated
            current_user.plan_generations_count += 1
            
            # Save the text-based schedule for persistence
            current_user.last_generated_schedule = json.dumps({'text': plan_text})
            current_user.last_schedule_date = datetime.now()
            db.session.commit()
            
            return jsonify({'plan': plan_text, 'structured': False})
    
    except Exception as e:
        return jsonify({'error': f'Error generating plan: {str(e)}'}), 500


def _build_planning_prompt(activities, now, current_date, current_time, 
                           weather_forecast, readiness_score, sleep_score, extra_info, last_activity, allow_multiple=False, injuries_pains=''):
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
        prompt += "\nScheduled Appointments & Responsibilities:\n"
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
    
    # Add last activity information
    if last_activity:
        prompt += f"\nLast Activity Completed:\n{last_activity}\n"
        prompt += "Consider this when planning to ensure proper recovery and variety.\n"
    
    # Add injuries/pains information
    if injuries_pains:
        prompt += f"\n⚠️ CURRENT INJURIES OR PAINS:\n{injuries_pains}\n"
        prompt += "CRITICAL: Avoid activities that could aggravate these conditions. Suggest modifications, lower intensity alternatives, or rest when appropriate. Prioritize recovery and safety.\n"
    
    # Add extra information
    if extra_info:
        prompt += f"\nAdditional Context:\n{extra_info}\n"
    
    # Add weather information and surface condition guidance
    if weather_forecast:
        temp_unit_display = current_user.temperature_unit or 'C'
        prompt += f"\nWeather forecast for {current_user.location} (with daylight hours):\n"
        for day in weather_forecast:
            # Include ground condition hints for planning
            wet = day.get('is_wet_ground')
            snowy = day.get('is_snowy_ground')
            windy = day.get('is_windy')
            wind_speed = day.get('wind_speed', 0)
            wind_gusts = day.get('wind_gusts', 0)
            cloud_cover = day.get('cloud_cover', 0) or 0
            weathercode = day.get('weathercode', 0) or 0
            
            # Determine precipitation type from weathercode
            precip_type = 'none'
            if weathercode in [95]:
                precip_type = 'thunderstorm'
            elif weathercode in [96, 99]:
                precip_type = 'thunderstorm with hail'
            elif weathercode in [71, 73, 75, 77, 85, 86]:
                precip_type = 'snow'
            elif weathercode in [56, 57, 66, 67]:
                precip_type = 'freezing rain'
            elif weathercode in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                precip_type = 'rain'
            
            short_term = ''
            if day.get('is_today'):
                nprecip = day.get('next3_precip_mm')
                nrain = day.get('next3_rain_mm')
                nsnow = day.get('next3_snow_mm')
                if nprecip is not None:
                    short_term = f" | next 3h: precip {nprecip}mm, rain {nrain or 0}mm, snow {nsnow or 0}mm"
            # Build surface/condition notes
            conditions = []
            if wet:
                conditions.append('wet')
            if snowy:
                conditions.append('snowy')
            if windy:
                conditions.append(f'windy (gusts {wind_gusts}mph)')
            if precip_type == 'thunderstorm' or precip_type == 'thunderstorm with hail':
                conditions.append(precip_type)
            surface_note = f" (Conditions: {', '.join(conditions)})" if conditions else ''
            
            # Include precipitation type in forecast line
            precip_info = f"Precipitation: {day['precipitation']}%"
            if precip_type != 'none':
                precip_info += f" ({precip_type})"
            
            prompt += f"- {day['date_short']}: {day['temp_max']}°{temp_unit_display}, {precip_info}, Cloud: {cloud_cover}%, Wind: {wind_speed}mph{short_term}, "
            prompt += f"Sunrise: {day['sunrise']}, Sunset: {day['sunset']}{surface_note}\n"
        prompt += "\nIMPORTANT: Consider sunrise/sunset times for outdoor activities that require daylight. Schedule outdoor activities during daylight hours only.\n"
        prompt += "If ground is wet or snowy, or if near-term rain/snow is expected (next 3h > 0mm), mark outdoor skateboarding/board sports as unsuitable and propose indoor alternatives (e.g., strength, mobility, stationary cardio).\n"
        prompt += "SNOW GUIDANCE: During snow conditions, avoid outdoor cycling, running, and activities requiring dry ground. Suggest indoor workouts or winter-specific activities like indoor training.\n"
        prompt += "THUNDERSTORM GUIDANCE: If thunderstorms are forecast, absolutely avoid ALL outdoor activities during that time. Prioritize safety and schedule indoor alternatives only.\n"
        prompt += "WIND GUIDANCE: If wind >= 15mph or gusts >= 25mph, avoid cycling, running on exposed routes, and outdoor activities affected by wind. Suggest indoor alternatives or sheltered locations.\n"
        prompt += "CLOUD GUIDANCE: High cloud cover (>80%) may reduce visibility and sunlight for outdoor activities like photography. Clear skies (<20%) are ideal for stargazing and outdoor photography.\n"
    
    # Add readiness and sleep scores
    if readiness_score or sleep_score:
        prompt += f"\nToday's Biometric Data (for {date_keys[0][1]} ONLY - do not apply to future days):\n"
        
        if readiness_score:
            prompt += f"- Readiness score: {readiness_score}/100"
            if readiness_score < 30:
                prompt += " (Low - prioritize recovery with lower intensity exercises like stretching and yoga)\n"
            elif readiness_score < 65:
                prompt += " (Moderate - heart rate and recent sleep are about usual, body is balancing stress with recovery)\n"
            else:
                prompt += " (High - body is well-rested and recovered, can handle intense activities)\n"
        
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
TASK: Create a balanced 7-day activity schedule optimized for the user's preferences, fitness level, and environmental conditions.

CRITICAL SCHEDULING RULES:
1. **Date-Specific Context**:
   - TODAY is {date_keys[0][1]} at {current_time}
   - If readiness/sleep scores provided, apply ONLY to today
   - For today's activities: respect current time (if evening, schedule evening activities; if morning, schedule morning activities)
   - Future days (days 2-7): plan based on preferences and weather only

2. **Appointment Conflicts** (MUST FOLLOW):
   - NEVER schedule activities that overlap with appointments
   - Leave buffer time before/after appointments
   - If appointment time unknown, assume morning slot unavailable

3. **Daylight Requirements** (MUST FOLLOW):
   - Outdoor activities requiring visibility MUST occur between sunrise and sunset
   - Examples requiring daylight: running, cycling, hiking, outdoor sports, photography
   - Indoor activities have no time restrictions

4. **Activity Distribution**:
   - Spread intensity levels across the week (no back-to-back high-intensity)
   - Honor preferred days/times when specified
   - Keep in mind recovery needs of different muscle groups and activity types to avoid overtraining any specific body part.
   - Match activities to optimal weather conditions
   - Try to keep the users preferred activity in mind when generating the plan.
{multiple_activities_instruction.replace('13.', '   -')}

5. **Weather Optimization**:
   - Schedule weather-dependent activities on best forecast days
   - Reserve backup indoor activities for poor weather days
   - Consider precipitation AND temperature for outdoor activities

DECISION FRAMEWORK:
- FOR TODAY: Readiness score → Intensity level → Time of day → Activity selection
- FOR FUTURE DAYS: Weather forecast → Activity dependencies → Time preferences → Schedule

OUTPUT FORMAT:
Return a valid JSON object with date keys mapping to activity details.
Use these EXACT date keys:
"""
    for date_key, day_name in date_keys:
        prompt += f'  "{date_key}": {{"day_name": "{day_name}", "activity": "Activity name or Rest", "time": "HH:MM", "duration_minutes": 60, "notes": "Brief explanation"}}\n'
    
    prompt += """
FIELD SPECIFICATIONS:
- "day_name": Use provided day names exactly as shown above
- "activity": Activity name from user's list, or "Rest" for recovery days
- "time": 24-hour format (HH:MM) based on:
  * Activity's preferred time if specified
  * Current time for today (schedule after current time)
  * Daylight hours for outdoor activities
  * Optimal time for activity type (e.g., running early morning, yoga evening)
- "duration_minutes": Integer based on activity's typical duration (default to activity duration if specified)
- "notes": 1-2 sentences explaining why this activity fits today (weather, recovery, timing)

RESPONSE REQUIREMENTS:
1. Return ONLY valid JSON - no markdown, no explanations, no code blocks
2. Use exact date keys provided above
3. Every date must have an entry (use "Rest" for recovery days)
4. Ensure all times are logical and follow daylight/appointment constraints
5. Notes should reference specific factors (weather, readiness, time of day)

Begin JSON output:
"""
    
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


@planning_bp.route('/check_calendar_conflicts', methods=['POST'])
@login_required
def check_calendar_conflicts():
    """Check if there are existing events from this app that would conflict with the export."""
    user_tier = current_user.subscription_tier or 'free_tier'
    if user_tier not in ['paid_tier', 'admin']:
        return jsonify({'error': 'Calendar export is only available for Paid and Admin tiers.'}), 403
    
    if not current_user.google_token:
        return jsonify({'error': 'Google account not connected.'}), 403
    
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        import pytz
        
        request_data = request.get_json() or {}
        plan_data = request_data.get('plan', {})
        
        if not plan_data:
            return jsonify({'error': 'No plan data provided'}), 400
        
        # Parse credentials (same as export function)
        if current_user.google_token.startswith('{'):
            credentials_dict = json.loads(current_user.google_token)
            creds = Credentials(
                token=credentials_dict.get('token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials_dict.get('client_id', config.GOOGLE_CLIENT_ID),
                client_secret=credentials_dict.get('client_secret', config.GOOGLE_CLIENT_SECRET),
                scopes=credentials_dict.get('scopes')
            )
        else:
            creds = Credentials(
                token=current_user.google_token,
                refresh_token=current_user.google_refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=config.GOOGLE_CLIENT_ID,
                client_secret=config.GOOGLE_CLIENT_SECRET,
                scopes=config.GOOGLE_SCOPES
            )
        
        # Refresh token if needed
        if creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                credentials_dict = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
                current_user.google_token = json.dumps(credentials_dict)
                current_user.google_refresh_token = creds.refresh_token
                db.session.commit()
            except Exception as refresh_error:
                return jsonify({
                    'error': 'Your Google connection has expired. Please disconnect and reconnect.',
                    'reconnect_required': True
                }), 401
        
        # Build calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Get timezone
        timezone = 'UTC'
        if current_user.location:
            temp_unit = current_user.temperature_unit or 'C'
            weather_data = get_weather_forecast(current_user.location, temp_unit)
            if weather_data:
                timezone = weather_data.get('timezone', 'UTC')
        
        tz = pytz.timezone(timezone)
        
        # Check for existing events with our tag
        plan_dates = list(plan_data.keys())
        if plan_dates:
            first_date = datetime.strptime(min(plan_dates), '%Y-%m-%d')
            last_date = datetime.strptime(max(plan_dates), '%Y-%m-%d') + timedelta(days=1)
            
            time_min = tz.localize(first_date).isoformat()
            time_max = tz.localize(last_date).isoformat()
            
            existing_events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                privateExtendedProperty='exportedFrom=aiActivityPlanner',
                singleEvents=True
            ).execute()
            
            existing_tagged_events = existing_events_result.get('items', [])
            
            if existing_tagged_events:
                return jsonify({
                    'hasConflicts': True,
                    'conflictCount': len(existing_tagged_events),
                    'message': f'Found {len(existing_tagged_events)} event(s) previously exported from this app in the same date range.'
                })
            else:
                return jsonify({
                    'hasConflicts': False,
                    'message': 'No conflicts found.'
                })
        else:
            return jsonify({
                'hasConflicts': False,
                'message': 'No plan dates to check.'
            })
    
    except Exception as e:
        import traceback
        print(f"Conflict check error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to check for conflicts: {str(e)}'}), 500


@planning_bp.route('/export_to_google_calendar', methods=['POST'])
@login_required
def export_to_google_calendar():
    """Export the generated plan to Google Calendar."""
    # Check subscription tier - only paid_tier and admin can export to calendar
    user_tier = current_user.subscription_tier or 'free_tier'
    if user_tier not in ['paid_tier', 'admin']:
        return jsonify({
            'error': 'Calendar export is only available for Paid and Admin tiers. Please upgrade your subscription to access this feature.',
            'upgrade_required': True
        }), 403
    
    if not current_user.google_token:
        return jsonify({'error': 'Google account not connected. Please connect your Google account first.'}), 403
    
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        import pytz
        
        request_data = request.get_json() or {}
        plan_data = request_data.get('plan', {})
        
        if not plan_data:
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
        
        # Always try to refresh if we have a refresh token (handles both expired and revoked tokens)
        if creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                print(f"[Calendar] Attempting to refresh token for user {current_user.id}")
                creds.refresh(Request())
                
                # Update stored token with new credentials
                credentials_dict = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes
                }
                current_user.google_token = json.dumps(credentials_dict)
                current_user.google_refresh_token = creds.refresh_token
                db.session.commit()
                print(f"[Calendar] Token refreshed successfully for user {current_user.id}")
            except Exception as refresh_error:
                print(f"[Calendar] Token refresh failed: {refresh_error}")
                return jsonify({
                    'error': 'Your Google connection has expired. Please disconnect and reconnect your Google account.',
                    'reconnect_required': True
                }), 401
        elif creds.expired:
            print(f"[Calendar] Token expired but no refresh token available")
            return jsonify({
                'error': 'Your Google connection has expired and cannot be refreshed. Please disconnect and reconnect your Google account.',
                'reconnect_required': True
            }), 401
        
        # Build Calendar API service
        try:
            service = build('calendar', 'v3', credentials=creds)
            print(f"[Calendar] Service built successfully for user {current_user.id}")
        except Exception as e:
            print(f"[Calendar] Service build failed: {e}")
            return jsonify({'error': f'Failed to connect to Google Calendar API. Please reconnect your Google account. Error: {str(e)}'}), 500
        
        # Get timezone from weather data (same as in generate_plan)
        # Note: We don't fetch calendar.get() because that requires calendar.readonly scope
        # The calendar.events scope only allows event operations, not calendar metadata
        timezone = 'UTC'
        if current_user.location:
            temp_unit = current_user.temperature_unit or 'C'
            weather_data = get_weather_forecast(current_user.location, temp_unit)
            if weather_data:
                timezone = weather_data.get('timezone', 'UTC')
        print(f"[Calendar] Using timezone: {timezone}")
        
        tz = pytz.timezone(timezone)
        events_created = 0
        events_updated = 0
        
        # Check for existing events with our tag (exported from this app)
        # We'll look for events in the date range of the plan
        plan_dates = list(plan_data.keys())
        if plan_dates:
            first_date = datetime.strptime(min(plan_dates), '%Y-%m-%d')
            last_date = datetime.strptime(max(plan_dates), '%Y-%m-%d') + timedelta(days=1)
            
            time_min = tz.localize(first_date).isoformat()
            time_max = tz.localize(last_date).isoformat()
            
            print(f"[Calendar] Checking for existing tagged events between {time_min} and {time_max}")
            
            try:
                existing_events_result = service.events().list(
                    calendarId='primary',
                    timeMin=time_min,
                    timeMax=time_max,
                    privateExtendedProperty='exportedFrom=aiActivityPlanner',
                    singleEvents=True
                ).execute()
                
                existing_tagged_events = existing_events_result.get('items', [])
                print(f"[Calendar] Found {len(existing_tagged_events)} existing tagged events")
                
                # Build a map of existing events by date for conflict checking
                existing_events_by_date = {}
                for evt in existing_tagged_events:
                    start = evt['start'].get('dateTime', evt['start'].get('date'))
                    if 'dateTime' in evt['start']:
                        evt_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date().isoformat()
                        existing_events_by_date[evt_date] = evt
                
                print(f"[Calendar] Existing events by date: {list(existing_events_by_date.keys())}")
            except Exception as e:
                print(f"[Calendar] Error checking existing events: {e}")
                existing_events_by_date = {}
        else:
            existing_events_by_date = {}
        
        print(f"[Calendar] Processing plan with {len(plan_data)} days")
        print(f"[Calendar] Plan keys: {list(plan_data.keys())}")
        
        # Create events for each day in the plan
        for date_key, day_data in plan_data.items():
            try:
                print(f"[Calendar] Processing day: {date_key}, data: {day_data}")
                # Parse the date
                event_date = datetime.strptime(date_key, '%Y-%m-%d').date()
                activity = day_data.get('activity', '')
                
                print(f"[Calendar] Activity for {date_key}: '{activity}'")
                
                # Skip rest days
                if 'rest' in activity.lower():
                    print(f"[Calendar] Skipping rest day: {date_key}")
                    continue
                
                # Get time and duration from plan, or use defaults
                activity_time = day_data.get('time', '09:00')
                duration_minutes = day_data.get('duration_minutes', 60)
                
                # Parse the time
                try:
                    hour, minute = map(int, activity_time.split(':'))
                    start_datetime = datetime.combine(event_date, datetime.min.time().replace(hour=hour, minute=minute))
                except (ValueError, AttributeError):
                    # Default to 9 AM if time parsing fails
                    start_datetime = datetime.combine(event_date, datetime.min.time().replace(hour=9))
                
                # Calculate end time based on duration
                end_datetime = start_datetime + timedelta(minutes=duration_minutes)
                print(f"[Calendar] Event time: {activity_time}, duration: {duration_minutes} min")
                
                # Localize to user's timezone
                start_datetime = tz.localize(start_datetime)
                end_datetime = tz.localize(end_datetime)
                
                # Build event description
                description = day_data.get('notes', '')
                if day_data.get('weather'):
                    description += f"\n\nWeather: {day_data['weather']}"
                
                # Create the event with our custom identifier tag
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
                    'extendedProperties': {
                        'private': {
                            'exportedFrom': 'aiActivityPlanner',
                            'exportedAt': datetime.utcnow().isoformat()
                        }
                    }
                }
                
                # Check if we have an existing event for this date
                if date_key in existing_events_by_date:
                    # Update the existing event instead of creating a new one
                    existing_event = existing_events_by_date[date_key]
                    event_id = existing_event['id']
                    print(f"[Calendar] Updating existing event {event_id} for {date_key}")
                    service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
                    events_updated += 1
                    print(f"[Calendar] Updated event for {date_key}: {activity}")
                else:
                    # Create new event
                    service.events().insert(calendarId='primary', body=event).execute()
                    events_created += 1
                    print(f"[Calendar] Created event for {date_key}: {activity}")
                
            except Exception as e:
                print(f"[Calendar] Error creating event for {date_key}: {e}")
                continue
        
        print(f"[Calendar] Total events created: {events_created}, updated: {events_updated}")
        
        if events_created == 0 and events_updated == 0:
            print("[Calendar] No events created or updated - returning error")
            return jsonify({
                'success': False,
                'message': 'No events were created. Your plan may only contain rest days.'
            }), 200
        
        # Build success message
        message_parts = []
        if events_created > 0:
            message_parts.append(f'created {events_created} new event{"s" if events_created != 1 else ""}')
        if events_updated > 0:
            message_parts.append(f'updated {events_updated} existing event{"s" if events_updated != 1 else ""}')
        
        message = f'Successfully {" and ".join(message_parts)}!'
        
        return jsonify({
            'success': True,
            'message': message,
            'created': events_created,
            'updated': events_updated
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
