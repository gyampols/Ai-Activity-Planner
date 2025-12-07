"""
Application configuration
Centralizes all environment variables and configuration settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///activities.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No timeout for CSRF tokens
    
    # OpenAI
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Base URL (for OAuth callbacks)
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    
    # OAuth Security (set to '1' for local development, '0' for production)
    OAUTHLIB_INSECURE_TRANSPORT = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '1')
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/fitness.activity.read',
        'https://www.googleapis.com/auth/fitness.body.read',
        'https://www.googleapis.com/auth/fitness.sleep.read'
    ]
    
    # Fitbit OAuth
    FITBIT_CLIENT_ID = os.environ.get('FITBIT_CLIENT_ID')
    FITBIT_CLIENT_SECRET = os.environ.get('FITBIT_CLIENT_SECRET')
    
    @property
    def GOOGLE_REDIRECT_URI(self):
        """Google OAuth login callback URI."""
        return f"{self.BASE_URL}/callback/google"
    
    @property
    def GOOGLE_CONNECT_REDIRECT_URI(self):
        """Google OAuth connect callback URI."""
        return f"{self.BASE_URL}/callback/connect-google"
    
    @property
    def FITBIT_REDIRECT_URI(self):
        """Fitbit OAuth callback URI."""
        return f"{self.BASE_URL}/callback/fitbit"


# Create a singleton instance
config = Config()
