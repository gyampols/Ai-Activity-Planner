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
            
            # Get readiness score (Premium feature)
            _fetch_fitbit_readiness(fitbit_headers, today)
            
            # Get sleep score (available to all users)
            _fetch_fitbit_sleep(fitbit_headers, today)
            
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
        
        if readiness_response.status_code == 200:
            readiness_data = readiness_response.json()
            if 'score' in readiness_data:
                current_user.fitbit_readiness_score = int(readiness_data['score'])
            elif 'value' in readiness_data:
                current_user.fitbit_readiness_score = int(readiness_data['value'])
            else:
                current_user.fitbit_readiness_score = None
        else:
            current_user.fitbit_readiness_score = None
    except Exception as e:
        print(f"Fitbit readiness fetch error: {e}")
        current_user.fitbit_readiness_score = None


def _fetch_fitbit_sleep(fitbit_headers, today):
    """Fetch sleep score from Fitbit API."""
    try:
        sleep_url = f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json"
        sleep_response = requests.get(sleep_url, headers=fitbit_headers, timeout=10)
        
        if sleep_response.status_code == 200:
            sleep_data = sleep_response.json()
            
            if sleep_data.get('sleep') and len(sleep_data['sleep']) > 0:
                sleep_log = sleep_data['sleep'][0]
                
                # Check for overall sleep score
                if 'sleepScore' in sleep_log:
                    current_user.fitbit_sleep_score = int(sleep_log['sleepScore'])
                elif 'efficiency' in sleep_log:
                    current_user.fitbit_sleep_score = int(sleep_log['efficiency'])
                else:
                    current_user.fitbit_sleep_score = None
                
                # Calculate readiness from sleep if not available
                if current_user.fitbit_readiness_score is None:
                    sleep_minutes = sleep_data.get('summary', {}).get('totalMinutesAsleep', 0)
                    if sleep_minutes > 0:
                        # Calculate readiness based on sleep (7-9 hours optimal)
                        if 420 <= sleep_minutes <= 540:  # 7-9 hours
                            current_user.fitbit_readiness_score = min(100, 85 + (sleep_minutes - 420) // 12)
                        elif sleep_minutes < 420:
                            current_user.fitbit_readiness_score = max(40, 85 - (420 - sleep_minutes) // 6)
                        else:
                            current_user.fitbit_readiness_score = max(70, 90 - (sleep_minutes - 540) // 10)
                    else:
                        current_user.fitbit_readiness_score = 75
            else:
                current_user.fitbit_sleep_score = None
                if current_user.fitbit_readiness_score is None:
                    current_user.fitbit_readiness_score = 75
        else:
            current_user.fitbit_sleep_score = None
            if current_user.fitbit_readiness_score is None:
                current_user.fitbit_readiness_score = 75
    except Exception as e:
        print(f"Fitbit sleep fetch error: {e}")
        current_user.fitbit_sleep_score = None
        if current_user.fitbit_readiness_score is None:
            current_user.fitbit_readiness_score = 75


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
        
        # Verify token and get user info
        idinfo = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            config.GOOGLE_CLIENT_ID
        )
        
        google_id = idinfo['sub']
        
        # Update current user's Google connection
        current_user.google_id = google_id
        current_user.google_token = credentials.token
        current_user.google_refresh_token = credentials.refresh_token
        
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
        current_user.google_id = None
        current_user.google_token = None
        current_user.google_refresh_token = None
        db.session.commit()
        flash('Google account disconnected successfully!', 'success')
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
