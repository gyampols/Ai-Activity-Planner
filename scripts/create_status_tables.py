#!/usr/bin/env python3
"""
Script to create status_change and status_change_types tables in aiactivityplanner database.
"""

import psycopg2

# Database connection settings
DB_HOST = "35.184.219.99"  # Cloud SQL public IP
DB_USER = "postgres"
DB_PASSWORD = "Gy072205"
DB_NAME = "aiactivityplanner"

def get_connection():
    """Create a connection to the database."""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode='require'
    )

def create_tables():
    """Create the status tracking tables."""
    print("=" * 60)
    print("Creating Status Tracking Tables")
    print("=" * 60)
    
    try:
        conn = get_connection()
        print(f"✓ Connected to database: {DB_NAME}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    try:
        with conn.cursor() as cur:
            # Create status_change_types table first (referenced by status_change)
            print("\n1. Creating status_change_types table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS status_change_types (
                    status_change_type_id SERIAL PRIMARY KEY,
                    status_change_type VARCHAR(100) NOT NULL UNIQUE
                )
            """)
            print("   ✓ status_change_types table created")
            
            # Create change_sources table (for tracking where the change came from)
            print("\n2. Creating change_sources table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS change_sources (
                    change_source_id SERIAL PRIMARY KEY,
                    change_source VARCHAR(100) NOT NULL UNIQUE
                )
            """)
            print("   ✓ change_sources table created")
            
            # Create status_change table with foreign keys
            print("\n3. Creating status_change table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS status_change (
                    status_id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    status_change_type_id INTEGER NOT NULL REFERENCES status_change_types(status_change_type_id),
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    change_source_id INTEGER REFERENCES change_sources(change_source_id),
                    old_value TEXT,
                    new_value TEXT
                )
            """)
            print("   ✓ status_change table created")
            
            # Create indexes for faster queries
            print("\n4. Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_change_user_id 
                ON status_change(user_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_change_timestamp 
                ON status_change(timestamp)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_change_type 
                ON status_change(status_change_type_id)
            """)
            print("   ✓ Indexes created")
            
            # Insert default status change types
            print("\n5. Inserting default status change types...")
            status_types = [
                'account_created',
                'account_deleted',
                'email_changed',
                'subscription_tier_changed',
                'test_flag_changed',
                'password_changed',
                'email_verified',
                'google_connected',
                'google_disconnected',
                'fitbit_connected',
                'fitbit_disconnected'
            ]
            
            for status_type in status_types:
                cur.execute("""
                    INSERT INTO status_change_types (status_change_type)
                    VALUES (%s)
                    ON CONFLICT (status_change_type) DO NOTHING
                """, (status_type,))
            print(f"   ✓ Inserted {len(status_types)} status change types")
            
            # Insert default change sources
            print("\n6. Inserting default change sources...")
            change_sources = [
                'user_action',
                'admin_action',
                'system_automatic',
                'api_call',
                'migration_script'
            ]
            
            for source in change_sources:
                cur.execute("""
                    INSERT INTO change_sources (change_source)
                    VALUES (%s)
                    ON CONFLICT (change_source) DO NOTHING
                """, (source,))
            print(f"   ✓ Inserted {len(change_sources)} change sources")
            
            conn.commit()
            print("\n✓ All tables created and populated successfully!")
            
            # Show what was created
            print("\n" + "=" * 60)
            print("Summary of Created Tables:")
            print("=" * 60)
            
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            print("\nAll tables in database:")
            for table in tables:
                print(f"  • {table[0]}")
            
            print("\nStatus change types:")
            cur.execute("SELECT * FROM status_change_types ORDER BY status_change_type_id")
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]}")
            
            print("\nChange sources:")
            cur.execute("SELECT * FROM change_sources ORDER BY change_source_id")
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    create_tables()
