"""
Database Migration Script
Adds new user profile fields to existing database.

Run this script when deploying to update the database schema.
Usage: python migrate_db.py
"""
import sqlite3
from pathlib import Path


def migrate_database():
    """Add new columns to the User table."""
    # Find database file
    db_path = Path('instance/activities.db')
    
    if not db_path.exists():
        # Try alternative name
        db_path = Path('instance/ai_planner.db')
        if not db_path.exists():
            print("Database not found. It will be created automatically when the app runs.")
            return
    
    print(f"Migrating database at {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns if they don't exist
        migrations = [
            ("full_name", "ALTER TABLE user ADD COLUMN full_name VARCHAR(200)"),
            ("age", "ALTER TABLE user ADD COLUMN age INTEGER"),
            ("gender", "ALTER TABLE user ADD COLUMN gender VARCHAR(50)"),
            ("height_cm", "ALTER TABLE user ADD COLUMN height_cm INTEGER"),
            ("weight_kg", "ALTER TABLE user ADD COLUMN weight_kg REAL"),
            ("timezone", "ALTER TABLE user ADD COLUMN timezone VARCHAR(100) DEFAULT 'UTC'"),
        ]
        
        for column_name, sql in migrations:
            if column_name not in columns:
                print(f"  Adding column: {column_name}")
                cursor.execute(sql)
            else:
                print(f"  Column {column_name} already exists, skipping")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()

