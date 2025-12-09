"""
AI Activity Planner - Main Application Entry Point

A Flask application that helps users plan their weekly activities based on:
- Weather forecasts
- Biometric data (Fitbit, Oura)
- Personal preferences
- AI-powered suggestions using OpenAI GPT-4

Modular architecture:
- config.py: All configuration and environment variables
- models.py: Database models
- utils/: Helper functions (weather, geolocation)
- routes/: Blueprint modules for different features
  - main.py: Basic pages and utility routes
  - auth.py: Authentication (login, signup, OAuth)
  - activities.py: Activity and appointment management
  - planning.py: AI-powered weekly planning
  - integrations.py: Third-party integrations (Fitbit, Google, Oura)
"""
import os
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import config
from models import db, User

# Import blueprints
from routes.main import main_bp
from routes.auth import auth_bp
from routes.activities import activities_bp
from routes.planning import planning_bp
from routes.integrations import integrations_bp
from routes.admin import admin_bp


def create_app():
    """Application factory pattern for creating the Flask app."""
    app = Flask(__name__)
    
    # Load configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['WTF_CSRF_ENABLED'] = config.WTF_CSRF_ENABLED
    app.config['WTF_CSRF_TIME_LIMIT'] = config.WTF_CSRF_TIME_LIMIT
    
    # Set OAuth security for development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = config.OAUTHLIB_INSECURE_TRANSPORT
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Configure login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(admin_bp)
    
    # Exempt CSRF for AJAX endpoints (they use same-origin policy)
    csrf.exempt(planning_bp)
    
    # Exempt calendar import endpoint for AJAX calls
    csrf.exempt(app.view_functions['integrations.import_calendar_events'])
    
    # Create database tables and run migrations
    with app.app_context():
        db.create_all()
        
        # Run migrations
        try:
            # Migration 1: Manual fitness scores
            db.session.execute(db.text('''
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS manual_readiness_score INTEGER,
                ADD COLUMN IF NOT EXISTS manual_sleep_score INTEGER,
                ADD COLUMN IF NOT EXISTS manual_score_date DATE;
            '''))
            
            # Migration 2: Subscription tiers
            db.session.execute(db.text('''
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(20) DEFAULT 'free_tier',
                ADD COLUMN IF NOT EXISTS plan_generations_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS plan_generation_reset_date DATE;
            '''))
            
            # Set admin tier for gregyampolsky accounts
            db.session.execute(db.text('''
                UPDATE "user"
                SET subscription_tier = 'admin'
                WHERE (LOWER(email) = 'gregyampolsky@gmail.com' OR LOWER(username) = 'gregyampolsky');
            '''))
            
            db.session.commit()
            print("✅ Database migrations completed")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Migration note: {e}")
    
    return app


# Create the application
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
