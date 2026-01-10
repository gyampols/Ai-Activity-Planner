"""
AI Activity Planner - Flask Application Factory.

A modular Flask application for AI-powered weekly activity planning.
"""
import os
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import config
from models import db, User
from routes.main import main_bp
from routes.auth import auth_bp
from routes.activities import activities_bp
from routes.planning import planning_bp
from routes.integrations import integrations_bp
from routes.admin import admin_bp
from routes.payment import payment_bp
from utils.logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application.
    
    Returns:
        Configured Flask application instance.
    """
    logger.info("Creating Flask application")
    app = Flask(__name__)
    _configure_app(app)
    _init_extensions(app)
    _register_blueprints(app)
    _run_migrations(app)
    return app


def _configure_app(app: Flask) -> None:
    """Apply all configuration settings to the app."""
    # Core Flask config
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['WTF_CSRF_ENABLED'] = config.WTF_CSRF_ENABLED
    app.config['WTF_CSRF_TIME_LIMIT'] = config.WTF_CSRF_TIME_LIMIT

    # Session and cookie security
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    # OAuth environment
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = config.OAUTHLIB_INSECURE_TRANSPORT


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    csrf = CSRFProtect(app)
    app.extensions['csrf'] = csrf

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id: str) -> User:
        return User.query.get(int(user_id))


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints and configure CSRF exemptions."""
    blueprints = [
        main_bp,
        auth_bp,
        activities_bp,
        planning_bp,
        integrations_bp,
        admin_bp,
        payment_bp,
    ]
    for bp in blueprints:
        app.register_blueprint(bp)

    # CSRF exemptions for AJAX and webhook endpoints
    csrf = app.extensions['csrf']
    csrf.exempt(planning_bp)
    csrf.exempt(app.view_functions['integrations.import_calendar_events'])
    csrf.exempt(app.view_functions['admin.toggle_test_flag'])
    csrf.exempt(app.view_functions['payment.stripe_webhook'])


def _run_migrations(app: Flask) -> None:
    """Create tables and run database migrations."""
    with app.app_context():
        db.create_all()
        _apply_schema_migrations()


def _apply_schema_migrations() -> None:
    """Apply database schema migrations idempotently."""
    try:
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS manual_readiness_score INTEGER,
            ADD COLUMN IF NOT EXISTS manual_sleep_score INTEGER,
            ADD COLUMN IF NOT EXISTS manual_score_date DATE;
        '''))
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free_tier',
            ADD COLUMN IF NOT EXISTS plan_generations_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS plan_generation_reset_date DATE;
        '''))
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS test_flag BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255),
            ADD COLUMN IF NOT EXISTS verification_token_expiry TIMESTAMP,
            ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255),
            ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP;
        '''))
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS has_paid_before BOOLEAN DEFAULT FALSE;
        '''))
        db.session.execute(db.text('''
            UPDATE "user"
            SET subscription_tier = 'admin'
            WHERE LOWER(email) = 'gregyampolsky@gmail.com' 
               OR LOWER(username) = 'gregyampolsky';
        '''))
        db.session.execute(db.text('''
            UPDATE "user"
            SET email_verified = TRUE
            WHERE email_verified = FALSE AND created_at < '2025-12-09';
        '''))
        
        # Add planning context fields (from cookies to DB)
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS last_completed_activity VARCHAR(500);
        '''))
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS current_injuries VARCHAR(500);
        '''))
        db.session.execute(db.text('''
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS additional_information TEXT;
        '''))
        
        db.session.commit()
        logger.info("Database migrations completed successfully")
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Migration note: {e}")


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
