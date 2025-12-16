"""
Add last_generated_schedule and last_schedule_date columns to user table.
Run this script to add schedule persistence columns.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

def add_columns():
    """Add the new columns to the user table."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name IN ('last_generated_schedule', 'last_schedule_date')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        
        if 'last_generated_schedule' not in existing_columns:
            print("Adding last_generated_schedule column...")
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN last_generated_schedule TEXT"))
            conn.commit()
            print("  Added last_generated_schedule column")
        else:
            print("  last_generated_schedule column already exists")
        
        if 'last_schedule_date' not in existing_columns:
            print("Adding last_schedule_date column...")
            conn.execute(text("ALTER TABLE \"user\" ADD COLUMN last_schedule_date TIMESTAMP"))
            conn.commit()
            print("  Added last_schedule_date column")
        else:
            print("  last_schedule_date column already exists")
    
    print("\nMigration complete!")

if __name__ == '__main__':
    add_columns()
