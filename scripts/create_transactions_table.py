#!/usr/bin/env python3
"""
Script to create transactions table in aiactivityplanner database.
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

def create_transactions_table():
    """Create the transactions table."""
    print("=" * 60)
    print("Creating Transactions Table")
    print("=" * 60)
    
    try:
        conn = get_connection()
        print(f"✓ Connected to database: {DB_NAME}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return
    
    try:
        with conn.cursor() as cur:
            # Create transactions table
            print("\n1. Creating transactions table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                    stripe_payment_intent_id VARCHAR(255) UNIQUE,
                    stripe_session_id VARCHAR(255),
                    amount_cents INTEGER NOT NULL,
                    currency VARCHAR(10) DEFAULT 'usd',
                    transaction_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    description TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata JSONB
                )
            """)
            print("   ✓ transactions table created")
            
            # Create indexes
            print("\n2. Creating indexes...")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_user_id 
                ON transactions(user_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_status 
                ON transactions(status)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_stripe_session 
                ON transactions(stripe_session_id)
            """)
            print("   ✓ Indexes created")
            
            # Add has_paid_before column to user table if not exists
            print("\n3. Adding has_paid_before column to user table...")
            cur.execute("""
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS has_paid_before BOOLEAN DEFAULT FALSE
            """)
            print("   ✓ has_paid_before column added")
            
            conn.commit()
            print("\n✓ All changes applied successfully!")
            
            # Show table structure
            print("\n" + "=" * 60)
            print("Transactions Table Structure:")
            print("=" * 60)
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'transactions'
                ORDER BY ordinal_position
            """)
            for row in cur.fetchall():
                print(f"  • {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
                
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    create_transactions_table()
