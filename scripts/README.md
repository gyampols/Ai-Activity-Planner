# Database Migration Scripts

One-time migration scripts used during development and deployment.
These have already been executed on production and are kept for reference only.

## Scripts

- `add_schedule_columns.py` - Added schedule persistence columns to user table
- `create_status_tables.py` - Created status_change audit tables
- `create_transactions_table.py` - Created Stripe transactions table
- `fix_transactions_column.py` - Fixed transaction column constraints
- `migrate_db.py` - Database migration utilities
- `migrate_users.py` - User data migration between databases
- `run_migration.py` - Migration runner script

## Note

These scripts are not required for normal application operation.
Database schema is now managed by SQLAlchemy models in `models.py` with
migrations applied automatically in `app.py` on startup.
