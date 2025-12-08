"""
Quick migration script to add manual score columns to production database
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db

def run_migration():
    """Run the database migration."""
    with app.app_context():
        print("Starting migration...")
        
        try:
            # Add columns if they don't exist
            db.session.execute(db.text('''
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS manual_readiness_score INTEGER,
                ADD COLUMN IF NOT EXISTS manual_sleep_score INTEGER,
                ADD COLUMN IF NOT EXISTS manual_score_date DATE;
            '''))
            db.session.commit()
            print("✅ Successfully added manual fitness score columns")
            return 0
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration error: {e}")
            return 1

if __name__ == '__main__':
    exit(run_migration())
