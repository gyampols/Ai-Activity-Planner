from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for Google-only accounts
    location = db.Column(db.String(200))  # City/location for weather
    temperature_unit = db.Column(db.String(1), default='C')  # 'C' or 'F'
    
    # Google OAuth fields
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    google_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    
    # User profile settings
    full_name = db.Column(db.String(200), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(50), nullable=True)  # Male, Female, Non-binary, Other, Prefer not to say
    height_cm = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    timezone = db.Column(db.String(100), default='UTC')
    
    # Fitness tracker integration
    fitbit_connected = db.Column(db.Boolean, default=False)
    fitbit_readiness_score = db.Column(db.Integer)  # Fitbit readiness score from API
    fitbit_sleep_score = db.Column(db.Integer)  # Fitbit sleep score from API
    fitbit_token = db.Column(db.Text, nullable=True)
    oura_connected = db.Column(db.Boolean, default=False)
    oura_readiness_score = db.Column(db.Integer)  # Mock readiness score
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activities = db.relationship('Activity', backref='user', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200))
    duration_minutes = db.Column(db.Integer)
    intensity = db.Column(db.String(50))  # Low, Medium, High
    dependencies = db.Column(db.Text)
    description = db.Column(db.Text)
    preferred_time = db.Column(db.String(50))  # Morning, Afternoon, Evening, Night
    preferred_days = db.Column(db.String(200))  # Comma-separated days: "Monday,Wednesday,Friday"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)  # Date of appointment
    time = db.Column(db.Time)  # Optional time
    duration_minutes = db.Column(db.Integer)  # Optional duration
    appointment_type = db.Column(db.String(50))  # Work, School, Doctor, Plans, Other
    repeating_days = db.Column(db.String(200))  # Comma-separated days (e.g., "Monday,Wednesday,Friday")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
