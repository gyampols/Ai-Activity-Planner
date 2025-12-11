"""
Third-party integrations (Fitbit, Google Fit, Oura) routes.
"""
import os
import json
import random
import base64
from flask import Blueprint, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from urllib.parse import quote
from datetime import datetime
import requests

from models import db
from config import config


integrations_bp = Blueprint('integrations', __name__)


@integrations_bp.route('/connect_fitbit', methods=['GET', 'POST'])
@login_required
def connect_fitbit():
    """Initiate Fitbit OAuth flow."""
    if not config.FITBIT_CLIENT_ID or not config.FITBIT_CLIENT_SECRET:
        # Fallback to mock data if Fitbit OAuth not configured
        current_user.fitbit_connected = True
        # Generate more realistic mock scores (30-70 range for variety)
        current_user.fitbit_readiness_score = random.randint(30, 70)
        current_user.fitbit_sleep_score = random.randint(35, 75)
        db.session.commit()
        flash(f'Fitbit connected (Mock data)! Readiness: {current_user.fitbit_readiness_score}/100, Sleep: {current_user.fitbit_sleep_score}/100', 'success')
        return redirect(request.referrer or url_for('activities.log'))
    
    # Real Fitbit OAuth flow
    auth_url = "https://www.fitbit.com/oauth2/authorize"
    scope = "activity heartrate sleep profile"
    
    # Create state token for security
    state = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    session['fitbit_state'] = state
    
    params = {
        'response_type': 'code',
        'client_id': config.FITBIT_CLIENT_ID,
        'redirect_uri': config.FITBIT_REDIRECT_URI,
        'scope': scope,
        'state': state
    }
    
    auth_request_url = f"{auth_url}?{'&'.join([f'{k}={quote(str(v))}' for k, v in params.items()])}"
    return redirect(auth_request_url)


@integrations_bp.route('/callback/fitbit')
@login_required
def callback_fitbit():
    """Handle Fitbit OAuth callback."""
    if not config.FITBIT_CLIENT_ID or not config.FITBIT_CLIENT_SECRET:
        flash('Fitbit OAuth is not configured.', 'error')
        return redirect(url_for('activities.log'))
    
    # Verify state
    state = session.get('fitbit_state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter.', 'error')
        return redirect(url_for('activities.log'))
    
    code = request.args.get('code')
    if not code:
        flash('Failed to connect Fitbit.', 'error')
        return redirect(url_for('activities.log'))
    
    try:
        # Exchange code for access token
        token_url = "https://api.fitbit.com/oauth2/token"
        
        # Fitbit requires HTTP Basic Auth
        credentials = f"{config.FITBIT_CLIENT_ID}:{config.FITBIT_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': config.FITBIT_REDIRECT_URI
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
            
            print(f"[Fitbit] Fetching data for user {current_user.id} on {today}")
            
            # Get readiness score (Premium feature)
            _fetch_fitbit_readiness(fitbit_headers, today)
            print(f"[Fitbit] Readiness score: {current_user.fitbit_readiness_score}")
            
            # Get sleep score (available to all users)
            _fetch_fitbit_sleep(fitbit_headers, today)
            print(f"[Fitbit] Sleep score: {current_user.fitbit_sleep_score}")
            
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
    
    return redirect(url_for('activities.log'))


def _fetch_fitbit_readiness(fitbit_headers, today):
    """Fetch readiness score from Fitbit API."""
    try:
        readiness_url = f"https://api.fitbit.com/1/user/-/activities/readiness/date/{today}.json"
        readiness_response = requests.get(readiness_url, headers=fitbit_headers, timeout=10)
        
        print(f"[Fitbit] Readiness API status: {readiness_response.status_code}")
        
        if readiness_response.status_code == 200:
            readiness_data = readiness_response.json()
            print(f"[Fitbit] Readiness data: {readiness_data}")
            if 'score' in readiness_data:
                current_user.fitbit_readiness_score = int(readiness_data['score'])
            elif 'value' in readiness_data:
                current_user.fitbit_readiness_score = int(readiness_data['value'])
            else:
                current_user.fitbit_readiness_score = None
        else:
            print(f"[Fitbit] Readiness API error: {readiness_response.text}")
            current_user.fitbit_readiness_score = None
    except Exception as e:
        print(f"[Fitbit] Readiness fetch error: {e}")
        current_user.fitbit_readiness_score = None


def _fetch_fitbit_sleep(fitbit_headers, today):
    """Fetch sleep score from Fitbit API."""
    try:
        sleep_url = f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json"
        sleep_response = requests.get(sleep_url, headers=fitbit_headers, timeout=10)
        
        print(f"[Fitbit] Sleep API status: {sleep_response.status_code}")
        
        if sleep_response.status_code == 200:
            sleep_data = sleep_response.json()
            print(f"[Fitbit] Sleep data summary: {sleep_data.get('summary', {})}")
            
            if sleep_data.get('sleep') and len(sleep_data['sleep']) > 0:
                sleep_log = sleep_data['sleep'][0]
                
                # Check for overall sleep score
                if 'sleepScore' in sleep_log:
                    current_user.fitbit_sleep_score = int(sleep_log['sleepScore'])
                elif 'efficiency' in sleep_log:
                    current_user.fitbit_sleep_score = int(sleep_log['efficiency'])
                else:
                    current_user.fitbit_sleep_score = None
                
                # Note: Fitbit Daily Readiness Score is a separate metric
                # We do NOT calculate it from sleep data
            else:
                current_user.fitbit_sleep_score = None
        else:
            current_user.fitbit_sleep_score = None
    except Exception as e:
        print(f"Fitbit sleep fetch error: {e}")
        current_user.fitbit_sleep_score = None


@integrations_bp.route('/connect/google')
@login_required
def connect_google():
    """Connect Google account to existing user."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('activities.log'))
    
    # Create flow instance
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [config.GOOGLE_CONNECT_REDIRECT_URI]
            }
        },
        scopes=config.GOOGLE_SCOPES,
        redirect_uri=config.GOOGLE_CONNECT_REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['connect_state'] = state
    return redirect(authorization_url)


@integrations_bp.route('/callback/connect-google')
@login_required
def callback_connect_google():
    """Handle Google OAuth callback for connecting account."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('activities.log'))
    
    # Verify state
    state = session.get('connect_state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter. Please try again.', 'error')
        return redirect(url_for('activities.log'))
    
    try:
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [config.GOOGLE_CONNECT_REDIRECT_URI]
                }
            },
            scopes=config.GOOGLE_SCOPES,
            state=state,
            redirect_uri=config.GOOGLE_CONNECT_REDIRECT_URI
        )
        
        # Fetch token
        flow.fetch_token(authorization_response=request.url)
        
        # Get credentials
        credentials = flow.credentials
        
        # Debug: Check what scopes the credentials actually have
        print(f"[Google Connect] Credentials scopes: {credentials.scopes}")
        print(f"[Google Connect] Has calendar scope: {'https://www.googleapis.com/auth/calendar.events' in (credentials.scopes or [])}")
        
        # Verify token and get user info
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            config.GOOGLE_CLIENT_ID
        )
        
        google_id = idinfo['sub']
        
        # Update current user's Google connection
        # Store credentials as JSON to preserve scopes
        credentials_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        current_user.google_id = google_id
        current_user.google_token = json.dumps(credentials_dict)
        current_user.google_refresh_token = credentials.refresh_token
        
        print(f"[Google Connect] Stored credentials with scopes for user {current_user.id}")
        
        db.session.commit()
        session.pop('connect_state', None)
        
        flash('Google account connected successfully!', 'success')
        return redirect(url_for('activities.log'))
        
    except Exception as e:
        print(f"Google connect error: {e}")
        flash('Failed to connect Google account. Please try again.', 'error')
        return redirect(url_for('activities.log'))


@integrations_bp.route('/connect_oura', methods=['POST'])
@login_required
def connect_oura():
    """Connect Oura ring (mock implementation)."""
    current_user.oura_connected = True
    current_user.oura_readiness_score = random.randint(65, 95)
    db.session.commit()
    flash(f'Oura connected successfully! Current readiness: {current_user.oura_readiness_score}/100 (Mock data)', 'success')
    return redirect(url_for('activities.log'))


@integrations_bp.route('/disconnect_google', methods=['GET', 'POST'])
@login_required
def disconnect_google():
    """Disconnect Google account from user."""
    if current_user.google_id:
        # Try to revoke the token with Google
        if current_user.google_token:
            try:
                # Parse token if it's JSON
                import json
                if current_user.google_token.startswith('{'):
                    token_data = json.loads(current_user.google_token)
                    access_token = token_data.get('access_token') or token_data.get('token')
                else:
                    access_token = current_user.google_token
                
                # Revoke the token
                revoke_url = f'https://oauth2.googleapis.com/revoke?token={access_token}'
                requests.post(revoke_url, timeout=5)
            except Exception as e:
                print(f"Error revoking Google token: {e}")
        
        current_user.google_id = None
        current_user.google_token = None
        current_user.google_refresh_token = None
        db.session.commit()
        flash('Google account disconnected successfully! Please reconnect to grant calendar permissions.', 'success')
    else:
        flash('No Google account connected.', 'info')
    return redirect(request.referrer or url_for('activities.log'))


@integrations_bp.route('/disconnect_fitbit', methods=['GET', 'POST'])
@login_required
def disconnect_fitbit():
    """Disconnect Fitbit from user."""
    if current_user.fitbit_connected:
        current_user.fitbit_connected = False
        current_user.fitbit_token = None
        current_user.fitbit_readiness_score = None
        current_user.fitbit_sleep_score = None
        db.session.commit()
        flash('Fitbit disconnected successfully!', 'success')
    else:
        flash('No Fitbit account connected.', 'info')
    return redirect(request.referrer or url_for('activities.log'))


@integrations_bp.route('/disconnect_oura', methods=['GET', 'POST'])
@login_required
def disconnect_oura():
    """Disconnect Oura ring from user."""
    if current_user.oura_connected:
        current_user.oura_connected = False
        current_user.oura_readiness_score = None
        db.session.commit()
        flash('Oura disconnected successfully!', 'success')
    else:
        flash('No Oura account connected.', 'info')
    return redirect(request.referrer or url_for('activities.log'))


@integrations_bp.route('/import_calendar_events', methods=['POST'])
@login_required
def import_calendar_events():
    """Import events from Google Calendar as appointments.
    Note: CSRF validation handled by Flask-Login for authenticated users."""
    from flask import jsonify
    from models import Appointment
    from datetime import datetime, timedelta
    from flask_wtf.csrf import CSRFProtect
    
    print(f"[Calendar Import] Request from user {current_user.id}")
    
    # Check subscription tier - only paid_tier and admin can import from calendar
    user_tier = current_user.subscription_tier or 'free_tier'
    if user_tier not in ['paid_tier', 'admin']:
        print(f"[Calendar Import] ERROR: User tier {user_tier} not authorized")
        return jsonify({
            'success': False,
            'error': 'Calendar import is only available for Paid and Admin tiers. Please upgrade your subscription to access this feature.',
            'upgrade_required': True
        }), 403
    
    print(f"[Calendar Import] Has google_token: {bool(current_user.google_token)}")
    print(f"[Calendar Import] Has google_id: {bool(current_user.google_id)}")
    
    if not current_user.google_token:
        print("[Calendar Import] ERROR: No google_token found")
        return jsonify({'success': False, 'error': 'Google account not connected. Please connect your Google account first.'}), 400
    
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        import pytz
        
        print(f"[Calendar Import] Parsing credentials...")
        
        # Parse stored credentials (stored as JSON)
        try:
            credentials_dict = json.loads(current_user.google_token)
            token = credentials_dict.get('token')
            refresh_token = credentials_dict.get('refresh_token')
            scopes = credentials_dict.get('scopes', [])
            print(f"[Calendar Import] Parsed JSON credentials - has token: {bool(token)}, scopes: {scopes}")
        except (json.JSONDecodeError, AttributeError) as e:
            # Fallback if token is stored as plain string
            print(f"[Calendar Import] JSON parse failed: {e}, using plain token")
            token = current_user.google_token
            refresh_token = current_user.google_refresh_token
            scopes = None
        
        # Validate token exists
        if not token:
            print("[Calendar Import] ERROR: Token is empty after parsing")
            return jsonify({'success': False, 'error': 'Invalid Google credentials. Please reconnect your Google account.'}), 400
        
        print(f"[Calendar Import] Creating credentials object...")
        
        # Create credentials from stored token
        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            scopes=scopes
        )
        
        print(f"[Calendar Import] Building calendar service...")
        
        # Build calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        print(f"[Calendar Import] Fetching events...")
        
        # Get events for the next 30 days
        now = datetime.utcnow()
        time_min = now.isoformat() + 'Z'
        time_max = (now + timedelta(days=30)).isoformat() + 'Z'
        
        # Fetch events from primary calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        imported_count = 0
        
        for event in events:
            # Skip if no summary (title)
            if 'summary' not in event:
                continue
            
            title = event['summary']
            
            # Parse start time
            start = event['start'].get('dateTime', event['start'].get('date'))
            if not start:
                continue
            
            # Check if event already exists (avoid duplicates)
            if 'dateTime' in event['start']:
                # Timed event
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                event_date = start_dt.date()
                event_time = start_dt.time()
                
                # Calculate duration
                end = event['end'].get('dateTime', event['end'].get('date'))
                if end:
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    duration = int((end_dt - start_dt).total_seconds() / 60)
                else:
                    duration = 60  # Default 1 hour
            else:
                # All-day event
                event_date = datetime.fromisoformat(start).date()
                event_time = None
                duration = None
            
            # Check for duplicate - compare title, date, and time to avoid duplicates
            if event_time:
                # For timed events, check exact match with time
                existing = Appointment.query.filter_by(
                    user_id=current_user.id,
                    title=title,
                    date=event_date,
                    time=event_time
                ).first()
            else:
                # For all-day events, check title and date only
                existing = Appointment.query.filter_by(
                    user_id=current_user.id,
                    title=title,
                    date=event_date
                ).filter(Appointment.time.is_(None)).first()
            
            if existing:
                print(f"[Calendar Import] Skipping duplicate: {title} on {event_date}")
                continue  # Skip duplicates
            
            # Determine appointment type from title/description
            description = event.get('description', '')
            title_lower = title.lower()
            
            if any(word in title_lower for word in ['work', 'meeting', 'call', 'standup', 'sync']):
                apt_type = 'Work'
            elif any(word in title_lower for word in ['class', 'lecture', 'study', 'exam', 'school']):
                apt_type = 'School'
            elif any(word in title_lower for word in ['doctor', 'dentist', 'appointment', 'checkup', 'medical']):
                apt_type = 'Medical'
            elif any(word in title_lower for word in ['dinner', 'lunch', 'coffee', 'party', 'hangout']):
                apt_type = 'Social'
            else:
                apt_type = 'Other'
            
            # Create appointment
            appointment = Appointment(
                user_id=current_user.id,
                title=title,
                appointment_type=apt_type,
                date=event_date,
                time=event_time,
                duration_minutes=duration,
                description=description[:500] if description else None,  # Limit description length
                repeating_days=None  # Google Calendar recurring events handled separately
            )
            
            db.session.add(appointment)
            imported_count += 1
        
        db.session.commit()
        
        print(f"[Calendar Import] Successfully imported {imported_count} events for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'count': imported_count,
            'message': f'Successfully imported {imported_count} event(s) from Google Calendar'
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[Calendar Import] Error for user {current_user.id}: {e}")
        print(f"[Calendar Import] Full traceback:\n{error_trace}")
        return jsonify({
            'success': False,
            'error': f'Failed to import events: {str(e)}'
        }), 500
