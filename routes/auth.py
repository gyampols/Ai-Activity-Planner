"""
Authentication routes for login, signup, logout, and OAuth flows.
"""
import json
from datetime import datetime
from typing import Optional

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from urllib.parse import urlparse, urljoin

from config import config
from models import db, User
from utils.email import (
    send_verification_email,
    send_password_reset_email,
    resend_verification_email,
)
from utils.status_logger import (
    log_account_created,
    log_email_verified,
    log_google_connected,
    log_password_changed,
)

auth_bp = Blueprint('auth', __name__)


def is_safe_url(target: str) -> bool:
    """Validate URL is safe for redirection to prevent open redirect attacks."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with username/password."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            flash('Username/email and password are required!', 'error')
            return render_template('login.html')
        
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user and user.check_password(password):
            # Check if email is verified
            if not user.email_verified:
                flash('Please verify your email before logging in. Check your inbox for the verification link.', 'warning')
                return render_template('login.html')
            
            login_user(user, remember=True)  # Remember user for 30 days
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username/email or password', 'error')
    
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
        
        # Set subscription tier (admin for gregyampolsky accounts, free_tier for everyone else)
        if email.lower() == 'gregyampolsky@gmail.com' or username.lower() == 'gregyampolsky':
            user.subscription_tier = 'admin'
            user.email_verified = True  # Auto-verify admin accounts
        else:
            user.subscription_tier = 'free_tier'
            user.email_verified = False  # Require verification for regular users
        
        db.session.add(user)
        db.session.commit()
        
        # Log account creation
        log_account_created(user.id, source='user_action')
        
        # Send verification email for non-admin users
        if not user.email_verified:
            app_url = request.url_root.rstrip('/')
            send_verification_email(user, app_url)
            flash('Account created! Please check your email to verify your account before logging in.', 'success')
        else:
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


@auth_bp.route('/login/google/warning')
def login_google_warning():
    """Show warning page before Google OAuth."""
    return render_template(
        'google_oauth_warning.html',
        continue_url=url_for('auth.login_google_continue'),
        back_url=url_for('auth.login')
    )


@auth_bp.route('/login/google')
def login_google():
    """Redirect to warning page first."""
    return redirect(url_for('auth.login_google_warning'))


@auth_bp.route('/login/google/continue')
def login_google_continue():
    """Initiate Google OAuth login flow after user confirms."""
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
    
    # Get state from request (session may be lost in Cloud Run)
    state = request.args.get('state')
    if not state:
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
        
        # Store credentials as JSON to preserve scopes
        credentials_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        credentials_json = json.dumps(credentials_dict)
        
        if not user:
            # Check if email already exists
            user = User.query.filter_by(email=email).first()
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                user.google_token = credentials_json
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
                    google_token=credentials_json,
                    google_refresh_token=credentials.refresh_token,
                    email_verified=True  # Google OAuth means email is verified
                )
                
                # Set subscription tier (admin for gregyampolsky accounts, free_tier for everyone else)
                if email.lower() == 'gregyampolsky@gmail.com' or username.lower() == 'gregyampolsky':
                    user.subscription_tier = 'admin'
                else:
                    user.subscription_tier = 'free_tier'
                
                db.session.add(user)
                db.session.commit()
                
                # Log account creation via Google OAuth
                log_account_created(user.id, source='user_action')
                log_google_connected(user.id, source='user_action')
        else:
            # Update tokens
            user.google_token = credentials_json
            if credentials.refresh_token:
                user.google_refresh_token = credentials.refresh_token
        
        db.session.commit()
        login_user(user, remember=True)  # Remember user for 30 days
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        flash('Failed to authenticate with Google. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/verify_email')
def verify_email():
    """Verify user email with token."""
    token = request.args.get('token')
    
    if not token:
        flash('Invalid verification link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Find user with this token
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        flash('Invalid or expired verification token.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check if token is expired
    if user.verification_token_expiry and user.verification_token_expiry < datetime.utcnow():
        flash('Verification link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.resend_verification'))
    
    # Verify the email
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    db.session.commit()
    
    # Log email verification
    log_email_verified(user.id, source='user_action')
    
    flash('Email verified successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification():
    """Resend verification email."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Please provide your email address.', 'danger')
            return render_template('resend_verification.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Don't reveal if email exists
            flash('If this email is registered, you will receive a verification link.', 'success')
            return redirect(url_for('auth.login'))
        
        if user.email_verified:
            flash('This email is already verified. You can log in.', 'success')
            return redirect(url_for('auth.login'))
        
        # Send verification email
        app_url = request.url_root.rstrip('/')
        resend_verification_email(user, app_url)
        
        flash('Verification email sent! Please check your inbox.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('resend_verification.html')


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Please provide your email address.', 'danger')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.password_hash:  # Only for non-OAuth users
            # Send reset email
            app_url = request.url_root.rstrip('/')
            send_password_reset_email(user, app_url)
        
        # Don't reveal if email exists
        flash('If this email is registered, you will receive a password reset link.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')


@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Reset password with token."""
    token = request.args.get('token')
    
    if not token:
        flash('Invalid reset link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Find user with this token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user:
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check if token is expired
    if user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow():
        flash('Reset link has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
        
        # Reset password
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        # Log password change
        log_password_changed(user.id, source='user_action')
        
        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', token=token)
