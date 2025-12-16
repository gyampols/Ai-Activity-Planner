"""
Application configuration.

Centralizes all environment variables and configuration settings
for Flask, database, OAuth providers, and external services.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Flask Core
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Database
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        'DATABASE_URL', 'sqlite:///activities.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # CSRF Protection
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT = None

    # OpenAI
    OPENAI_API_KEY: str = os.environ.get('OPENAI_API_KEY', '')

    # Application URLs
    BASE_URL: str = os.environ.get('BASE_URL', 'http://localhost:5000')
    OAUTHLIB_INSECURE_TRANSPORT: str = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '1')

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET: str = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_DISCOVERY_URL: str = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_SCOPES: list = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/fitness.activity.read',
        'https://www.googleapis.com/auth/fitness.body.read',
        'https://www.googleapis.com/auth/fitness.sleep.read',
        'https://www.googleapis.com/auth/calendar.events',
    ]

    # Fitbit OAuth
    FITBIT_CLIENT_ID: str = os.environ.get('FITBIT_CLIENT_ID', '')
    FITBIT_CLIENT_SECRET: str = os.environ.get('FITBIT_CLIENT_SECRET', '')

    # Stripe Payments
    STRIPE_SECRET_KEY: str = os.environ.get('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLISHABLE_KEY: str = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
    STRIPE_WEBHOOK_SECRET: str = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    STRIPE_PRICE_ID: str = os.environ.get('STRIPE_PRICE_ID', '')
    
    @property
    def GOOGLE_REDIRECT_URI(self) -> str:
        """OAuth callback URI for Google login."""
        return f"{self.BASE_URL}/callback/google"

    @property
    def GOOGLE_CONNECT_REDIRECT_URI(self) -> str:
        """OAuth callback URI for Google account connection."""
        return f"{self.BASE_URL}/callback/connect-google"

    @property
    def FITBIT_REDIRECT_URI(self) -> str:
        """OAuth callback URI for Fitbit connection."""
        return f"{self.BASE_URL}/callback/fitbit"


config = Config()
