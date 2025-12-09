"""
Email utility functions for sending verification and password reset emails.
"""
import os
import secrets
from datetime import datetime, timedelta
from flask import url_for


def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def send_verification_email(user, app_url):
    """
    Send email verification link to user.
    
    For now, this is a placeholder that logs the verification URL.
    In production, integrate with SendGrid, AWS SES, or similar service.
    """
    from models import db
    
    # Generate verification token
    token = generate_token()
    user.verification_token = token
    user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    
    # Build verification URL
    verification_url = f"{app_url}/verify_email?token={token}"
    
    # Log for development (replace with actual email sending in production)
    print(f"""
    =====================================
    EMAIL VERIFICATION
    =====================================
    To: {user.email}
    Subject: Verify Your Email - AI Activity Planner
    
    Hi {user.username},
    
    Please verify your email address by clicking the link below:
    {verification_url}
    
    This link will expire in 24 hours.
    
    If you didn't create this account, please ignore this email.
    
    Best regards,
    AI Activity Planner Team
    =====================================
    """)
    
    return verification_url


def send_password_reset_email(user, app_url):
    """
    Send password reset link to user.
    
    For now, this is a placeholder that logs the reset URL.
    In production, integrate with SendGrid, AWS SES, or similar service.
    """
    from models import db
    
    # Generate reset token
    token = generate_token()
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()
    
    # Build reset URL
    reset_url = f"{app_url}/reset_password?token={token}"
    
    # Log for development (replace with actual email sending in production)
    print(f"""
    =====================================
    PASSWORD RESET
    =====================================
    To: {user.email}
    Subject: Reset Your Password - AI Activity Planner
    
    Hi {user.username},
    
    You requested to reset your password. Click the link below to proceed:
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    AI Activity Planner Team
    =====================================
    """)
    
    return reset_url


def resend_verification_email(user, app_url):
    """Resend verification email to user."""
    return send_verification_email(user, app_url)
