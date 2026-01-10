"""
Migration: Add planning context fields to User table.

Adds last_completed_activity, current_injuries, and additional_information
columns to store data previously kept in cookies.
"""
from sqlalchemy import text

def upgrade(db_session):
    """Add planning context columns to user table."""
    try:
        # Add last_completed_activity column
        db_session.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS last_completed_activity VARCHAR(500)
        """))
        
        # Add current_injuries column
        db_session.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS current_injuries VARCHAR(500)
        """))
        
        # Add additional_information column
        db_session.execute(text("""
            ALTER TABLE "user" 
            ADD COLUMN IF NOT EXISTS additional_information TEXT
        """))
        
        db_session.commit()
        print("✓ Successfully added planning context fields to user table")
        
    except Exception as e:
        db_session.rollback()
        print(f"✗ Error adding planning context fields: {e}")
        raise


def downgrade(db_session):
    """Remove planning context columns from user table."""
    try:
        db_session.execute(text("""
            ALTER TABLE "user" 
            DROP COLUMN IF EXISTS last_completed_activity,
            DROP COLUMN IF EXISTS current_injuries,
            DROP COLUMN IF EXISTS additional_information
        """))
        
        db_session.commit()
        print("✓ Successfully removed planning context fields from user table")
        
    except Exception as e:
        db_session.rollback()
        print(f"✗ Error removing planning context fields: {e}")
        raise


if __name__ == '__main__':
    import os
    import sys
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create engine and session
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("Running migration: add_planning_context_fields")
        upgrade(session)
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        session.close()
