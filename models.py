"""
Database models for the AI Activity Planner application.

This module defines all SQLAlchemy ORM models including User, Activity,
Appointment, and audit/transaction tracking tables.
"""
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model with authentication and profile data."""
    
    __tablename__ = 'user'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(255), nullable=True)
    verification_token_expiry = db.Column(db.DateTime, nullable=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # OAuth
    google_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    google_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    
    # Profile
    full_name = db.Column(db.String(200), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(50), nullable=True)
    height_cm = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Float, nullable=True)
    timezone = db.Column(db.String(100), default='UTC')
    location = db.Column(db.String(200), nullable=True)
    temperature_unit = db.Column(db.String(1), default='C')
    
    # Fitness trackers
    fitbit_connected = db.Column(db.Boolean, default=False)
    fitbit_token = db.Column(db.Text, nullable=True)
    fitbit_readiness_score = db.Column(db.Integer, nullable=True)
    fitbit_sleep_score = db.Column(db.Integer, nullable=True)
    oura_connected = db.Column(db.Boolean, default=False)
    oura_readiness_score = db.Column(db.Integer, nullable=True)
    
    # Manual fitness scores
    manual_readiness_score = db.Column(db.Integer, nullable=True)
    manual_sleep_score = db.Column(db.Integer, nullable=True)
    manual_score_date = db.Column(db.Date, nullable=True)
    
    # Subscription
    subscription_tier = db.Column(db.String(20), default='free_tier', nullable=False)
    plan_generations_count = db.Column(db.Integer, default=0, nullable=False)
    plan_generation_reset_date = db.Column(db.Date, nullable=True)
    has_paid_before = db.Column(db.Boolean, default=False, nullable=False)
    
    # Schedule persistence
    last_generated_schedule = db.Column(db.Text, nullable=True)
    last_schedule_date = db.Column(db.DateTime, nullable=True)
    
    # Admin
    test_flag = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    activities = db.relationship(
        'Activity', backref='user', lazy=True, cascade='all, delete-orphan'
    )
    appointments = db.relationship(
        'Appointment', backref='user', lazy=True, cascade='all, delete-orphan'
    )

    def set_password(self, password: str) -> None:
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.subscription_tier == 'admin'
    
    @property
    def is_paid(self) -> bool:
        """Check if user has paid tier access."""
        return self.subscription_tier in ('paid_tier', 'admin')

    def __repr__(self) -> str:
        return f'<User {self.username}>'


class Activity(db.Model):
    """User-defined activity for planning."""
    
    __tablename__ = 'activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    intensity = db.Column(db.String(50), nullable=True)
    dependencies = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    preferred_time = db.Column(db.String(50), nullable=True)
    preferred_days = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f'<Activity {self.name}>'


class Appointment(db.Model):
    """User calendar appointment for schedule constraints."""
    
    __tablename__ = 'appointment'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    appointment_type = db.Column(db.String(50), nullable=True)
    repeating_days = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f'<Appointment {self.title} on {self.date}>'


class StatusChangeType(db.Model):
    """Lookup table for status change categories."""
    
    __tablename__ = 'status_change_types'
    
    id = db.Column('status_change_type_id', db.Integer, primary_key=True)
    name = db.Column('status_change_type', db.String(100), unique=True, nullable=False)
    
    status_changes = db.relationship('StatusChange', backref='change_type', lazy=True)

    def __repr__(self) -> str:
        return f'<StatusChangeType {self.name}>'


class ChangeSource(db.Model):
    """Lookup table for change origin tracking."""
    
    __tablename__ = 'change_sources'
    
    id = db.Column('change_source_id', db.Integer, primary_key=True)
    name = db.Column('change_source', db.String(100), unique=True, nullable=False)
    
    status_changes = db.relationship('StatusChange', backref='source', lazy=True)

    def __repr__(self) -> str:
        return f'<ChangeSource {self.name}>'


class StatusChange(db.Model):
    """Audit log for tracking user account changes."""
    
    __tablename__ = 'status_change'
    
    id = db.Column('status_id', db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('user.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    status_change_type_id = db.Column(
        db.Integer, 
        db.ForeignKey('status_change_types.status_change_type_id'), 
        nullable=False
    )
    change_source_id = db.Column(
        db.Integer, 
        db.ForeignKey('change_sources.change_source_id'), 
        nullable=True
    )
    changed_by_user_id = db.Column(
        db.Integer, 
        db.ForeignKey('user.id', ondelete='SET NULL'), 
        nullable=True
    )
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = db.relationship(
        'User', 
        foreign_keys=[user_id], 
        backref=db.backref('status_changes', lazy=True)
    )
    changed_by = db.relationship(
        'User', 
        foreign_keys=[changed_by_user_id], 
        backref=db.backref('changes_made', lazy=True)
    )

    def __repr__(self) -> str:
        return f'<StatusChange {self.id} for user {self.user_id}>'


class Transaction(db.Model):
    """Payment transaction record for Stripe payments."""
    
    __tablename__ = 'transactions'
    
    id = db.Column('transaction_id', db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey('user.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    stripe_payment_intent_id = db.Column(db.String(255), unique=True, nullable=True)
    stripe_session_id = db.Column(db.String(255), nullable=True, index=True)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(10), default='usd', nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)
    description = db.Column(db.Text, nullable=True)
    transaction_metadata = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))

    def __repr__(self) -> str:
        return f'<Transaction {self.id} - {self.status}>'
