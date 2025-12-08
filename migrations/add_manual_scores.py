"""
Database migration script for AI Activity Planner.
Adds manual fitness score fields to User model.
"""
from app import app, db
from models import User

def migrate():
    """Run database migrations."""
    with app.app_context():
        print("Starting migration...")
        
        # Add new columns if they don't exist
        try:
            db.session.execute(db.text('''
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS manual_readiness_score INTEGER,
                ADD COLUMN IF NOT EXISTS manual_sleep_score INTEGER,
                ADD COLUMN IF NOT EXISTS manual_score_date DATE
            '''))
            db.session.commit()
            print("✅ Successfully added manual fitness score columns")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Migration error (columns may already exist): {e}")
        
        print("Migration complete!")

if __name__ == '__main__':
    migrate()
