"""
Authentication routes including login, signup, and OAuth flows.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from urllib.parse import urlparse, urljoin

from models import db, User
from config import config


auth_bp = Blueprint('auth', __name__)


def is_safe_url(target):
    """Check if a URL is safe to redirect to (prevents open redirects)."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with username/password."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
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
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
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
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return render_template('signup.html')
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/login/google')
def login_google():
    """Initiate Google OAuth login flow."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured. Please contact the administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    # Create flow instance
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": config.GOOGLE_CLIENT_ID,
                "client_secret": config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [config.GOOGLE_REDIRECT_URI]
            }
        },
        scopes=config.GOOGLE_SCOPES,
        redirect_uri=config.GOOGLE_REDIRECT_URI
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['state'] = state
    return redirect(authorization_url)


@auth_bp.route('/callback/google')
def callback_google():
    """Handle Google OAuth callback for login."""
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('auth.login'))
    
    # Verify state
    state = session.get('state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        # Create flow instance
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [config.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=config.GOOGLE_SCOPES,
            state=state,
            redirect_uri=config.GOOGLE_REDIRECT_URI
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
        email = idinfo.get('email')
        
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
        return redirect(url_for('main.index'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Failed to authenticate with Google. Please try again.', 'error')
        return redirect(url_for('auth.login'))
