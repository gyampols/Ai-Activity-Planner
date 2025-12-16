#!/usr/bin/env python3
"""
Migration script to copy users from ai_activity_planner to aiactivityplanner database.
Uses email to identify unique users and avoids duplicates.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection settings
DB_HOST = "35.184.219.99"  # Cloud SQL public IP
DB_USER = "postgres"
DB_PASSWORD = "Gy072205"

SOURCE_DB = "ai_activity_planner"
TARGET_DB = "aiactivityplanner"

def get_connection(database):
    """Create a connection to the specified database."""
    return psycopg2.connect(
        host=DB_HOST,
        database=database,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode='require'
    )

def get_all_users(conn):
    """Get all users from a database."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM \"user\" ORDER BY id")
        return cur.fetchall()

def get_existing_emails(conn):
    """Get all existing emails from the target database."""
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM \"user\"")
        return {row[0].lower() for row in cur.fetchall()}

def get_max_id(conn):
    """Get the maximum user ID in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM \"user\"")
        return cur.fetchone()[0]

def migrate_users():
    """Main migration function."""
    print("=" * 60)
    print("User Migration: ai_activity_planner -> aiactivityplanner")
    print("=" * 60)
    
    # Connect to both databases
    try:
        source_conn = get_connection(SOURCE_DB)
        print(f"✓ Connected to source database: {SOURCE_DB}")
    except Exception as e:
        print(f"✗ Failed to connect to source database: {e}")
        return
    
    try:
        target_conn = get_connection(TARGET_DB)
        print(f"✓ Connected to target database: {TARGET_DB}")
    except Exception as e:
        print(f"✗ Failed to connect to target database: {e}")
        source_conn.close()
        return
    
    try:
        # Get users from source
        source_users = get_all_users(source_conn)
        print(f"\nSource database has {len(source_users)} users")
        
        # Get existing emails in target
        existing_emails = get_existing_emails(target_conn)
        print(f"Target database has {len(existing_emails)} existing emails")
        
        # Find users to migrate (not already in target by email)
        users_to_migrate = []
        for user in source_users:
            if user['email'].lower() not in existing_emails:
                users_to_migrate.append(user)
        
        print(f"\nUsers to migrate: {len(users_to_migrate)}")
        
        if not users_to_migrate:
            print("\n✓ No users need to be migrated. All emails already exist in target.")
            return
        
        # Get max ID in target to assign new IDs
        max_target_id = get_max_id(target_conn)
        print(f"Current max ID in target: {max_target_id}")
        
        # Prepare insert statement with all columns
        columns = [
            'id', 'username', 'email', 'password_hash', 'location', 'temperature_unit',
            'google_id', 'google_token', 'google_refresh_token',
            'full_name', 'age', 'gender', 'height_cm', 'weight_kg', 'timezone',
            'fitbit_connected', 'fitbit_readiness_score', 'fitbit_sleep_score', 'fitbit_token',
            'oura_connected', 'oura_readiness_score',
            'manual_readiness_score', 'manual_sleep_score', 'manual_score_date',
            'subscription_tier', 'plan_generations_count', 'plan_generation_reset_date',
            'test_flag', 'email_verified', 'verification_token', 'verification_token_expiry',
            'reset_token', 'reset_token_expiry', 'created_at'
        ]
        
        # Insert users
        migrated_count = 0
        with target_conn.cursor() as cur:
            for user in users_to_migrate:
                max_target_id += 1
                new_id = max_target_id
                
                # Build values list, using new ID
                values = []
                for col in columns:
                    if col == 'id':
                        values.append(new_id)
                    elif col in user:
                        values.append(user[col])
                    else:
                        # Column might not exist in source, use default
                        if col == 'temperature_unit':
                            values.append('C')
                        elif col == 'subscription_tier':
                            values.append('free_tier')
                        elif col == 'plan_generations_count':
                            values.append(0)
                        elif col in ('fitbit_connected', 'oura_connected', 'test_flag', 'email_verified'):
                            values.append(False)
                        elif col == 'timezone':
                            values.append('UTC')
                        else:
                            values.append(None)
                
                # Check for username conflict and make unique if needed
                username = user.get('username', user['email'].split('@')[0])
                cur.execute("SELECT COUNT(*) FROM \"user\" WHERE username = %s", (username,))
                if cur.fetchone()[0] > 0:
                    # Username exists, append number
                    base_username = username
                    counter = 1
                    while True:
                        username = f"{base_username}_{counter}"
                        cur.execute("SELECT COUNT(*) FROM \"user\" WHERE username = %s", (username,))
                        if cur.fetchone()[0] == 0:
                            break
                        counter += 1
                
                # Update username in values
                username_idx = columns.index('username')
                values[username_idx] = username
                
                # Build and execute INSERT
                placeholders = ', '.join(['%s'] * len(columns))
                col_names = ', '.join([f'"{c}"' for c in columns])
                
                insert_sql = f'INSERT INTO "user" ({col_names}) VALUES ({placeholders})'
                
                try:
                    cur.execute(insert_sql, values)
                    print(f"  ✓ Migrated: {user['email']} (old ID: {user['id']} -> new ID: {new_id}, username: {username})")
                    migrated_count += 1
                except Exception as e:
                    print(f"  ✗ Failed to migrate {user['email']}: {e}")
                    target_conn.rollback()
                    continue
        
        # Commit all changes
        target_conn.commit()
        print(f"\n✓ Successfully migrated {migrated_count} users")
        
        # Verify final counts
        target_users = get_all_users(target_conn)
        print(f"\nFinal target database user count: {len(target_users)}")
        
        # Check for any duplicates
        with target_conn.cursor() as cur:
            cur.execute("""
                SELECT email, COUNT(*) as cnt 
                FROM "user" 
                GROUP BY email 
                HAVING COUNT(*) > 1
            """)
            duplicates = cur.fetchall()
            if duplicates:
                print(f"\n⚠ Warning: Found duplicate emails: {duplicates}")
            else:
                print("✓ No duplicate emails in target database")
            
            cur.execute("""
                SELECT id, COUNT(*) as cnt 
                FROM "user" 
                GROUP BY id 
                HAVING COUNT(*) > 1
            """)
            id_duplicates = cur.fetchall()
            if id_duplicates:
                print(f"⚠ Warning: Found duplicate IDs: {id_duplicates}")
            else:
                print("✓ No duplicate IDs in target database")
        
    except Exception as e:
        print(f"\n✗ Migration error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        source_conn.close()
        target_conn.close()
        print("\n✓ Database connections closed")

if __name__ == "__main__":
    migrate_users()
