"""
Email utility functions for verification and password reset.
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional


def generate_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(32)


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Send email using SendGrid API.

    Falls back to console logging if SendGrid is not configured.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        html_content: HTML body content.

    Returns:
        True if email sent successfully, False otherwise.
    """
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('EMAIL_FROM', 'noreply@aiactivityplanner.com')
    
    if not sendgrid_api_key:
        # Fallback to console logging for development
        print(f"""
        =====================================
        EMAIL (Development Mode - No SendGrid Key)
        =====================================
        To: {to_email}
        From: {from_email}
        Subject: {subject}
        
        {html_content}
        =====================================
        """)
        return False
    
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
        
        sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
        
        mail = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        response = sg.client.mail.send.post(request_body=mail.get())
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Email sent successfully to {to_email}")
            return True
        else:
            print(f"⚠️ SendGrid returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending email via SendGrid: {str(e)}")
        # Still log the email for development purposes
        print(f"""
        =====================================
        EMAIL (SendGrid Error)
        =====================================
        To: {to_email}
        From: {from_email}
        Subject: {subject}
        
        {html_content}
        =====================================
        """)
        return False


def send_verification_email(user, app_url):
    """
    Send email verification link to user.
    """
    from models import db
    
    # Generate verification token
    token = generate_token()
    user.verification_token = token
    user.verification_token_expiry = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    
    # Build verification URL
    verification_url = f"{app_url}/verify_email?token={token}"
    
    # Email subject and content
    subject = "Verify Your Email - AI Activity Planner"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✉️ Verify Your Email</h1>
            </div>
            <div class="content">
                <h2>Hi {user.username}!</h2>
                <p>Thank you for signing up for AI Activity Planner. To complete your registration, please verify your email address by clicking the button below:</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #fff; padding: 10px; border-radius: 5px;">{verification_url}</p>
                <p><strong>This link will expire in 24 hours.</strong></p>
                <p>If you didn't create this account, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>© 2025 AI Activity Planner. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    send_email(user.email, subject, html_content)
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
    
    # Email subject and content
    subject = "Reset Your Password - AI Activity Planner"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 15px 30px; background: #e74c3c; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hi {user.username},</h2>
                <p>You requested to reset your password for your AI Activity Planner account. Click the button below to set a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #fff; padding: 10px; border-radius: 5px;">{reset_url}</p>
                <div class="warning">
                    <strong>⚠️ Important:</strong> This link will expire in 1 hour for security reasons.
                </div>
                <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
            </div>
            <div class="footer">
                <p>© 2025 AI Activity Planner. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    send_email(user.email, subject, html_content)
    return reset_url


def resend_verification_email(user, app_url):
    """Resend verification email to user."""
    return send_verification_email(user, app_url)
