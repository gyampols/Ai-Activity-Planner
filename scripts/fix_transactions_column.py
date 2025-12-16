#!/usr/bin/env python3
"""
Migration script to rename 'metadata' column to 'transaction_metadata' in transactions table.
"""
import os
import psycopg2

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:Gy072205@35.184.219.99:5432/aiactivityplanner')

def run_migration():
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Check if the old column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'transactions' AND column_name = 'metadata';
        """)
        
        if cur.fetchone():
            print("Found 'metadata' column - renaming to 'transaction_metadata'...")
            cur.execute("ALTER TABLE transactions RENAME COLUMN metadata TO transaction_metadata;")
            conn.commit()
            print("✅ Successfully renamed column!")
        else:
            # Check if new column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transactions' AND column_name = 'transaction_metadata';
            """)
            if cur.fetchone():
                print("✅ Column 'transaction_metadata' already exists - no migration needed.")
            else:
                print("⚠️ Neither 'metadata' nor 'transaction_metadata' column found.")
                # Add the column if it doesn't exist
                print("Adding 'transaction_metadata' column...")
                cur.execute("ALTER TABLE transactions ADD COLUMN transaction_metadata JSON;")
                conn.commit()
                print("✅ Added 'transaction_metadata' column!")
                
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run_migration()
