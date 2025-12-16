"""
Status change logging utility for user audit trails.

Provides functions to log user account changes including subscriptions,
email changes, password resets, and OAuth connections.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from models import db, StatusChange, StatusChangeType, ChangeSource

_type_cache: Dict[str, int] = {}
_source_cache: Dict[str, int] = {}


def get_status_type_id(type_name: str) -> Optional[int]:
    """Get cached status_change_type_id for a given type name."""
    if type_name in _type_cache:
        return _type_cache[type_name]

    status_type = StatusChangeType.query.filter_by(name=type_name).first()
    if status_type:
        _type_cache[type_name] = status_type.id
        return status_type.id
    return None


def get_source_id(source_name: str) -> Optional[int]:
    """Get cached change_source_id for a given source name."""
    if source_name in _source_cache:
        return _source_cache[source_name]

    source = ChangeSource.query.filter_by(name=source_name).first()
    if source:
        _source_cache[source_name] = source.id
        return source.id
    return None


def log_status_change(
    user_id: int,
    change_type: str,
    source: str = 'system_automatic',
    old_value: Any = None,
    new_value: Any = None,
    changed_by_user_id: Optional[int] = None,
) -> Optional[StatusChange]:
    """
    Log a status change event for a user.

    Args:
        user_id: Target user's ID
        change_type: Type of change (e.g., 'account_created', 'subscription_tier_changed')
        source: Origin of change ('user_action', 'admin_action', 'system_automatic')
        old_value: Previous value (optional)
        new_value: New value (optional)
        changed_by_user_id: Admin user ID who made the change (optional)

    Returns:
        StatusChange object if successful, None otherwise
    """
    try:
        type_id = get_status_type_id(change_type)
        source_id = get_source_id(source)
        
        if not type_id:
            print(f"Warning: Unknown status change type: {change_type}")
            return None
        
        status_change = StatusChange(
            user_id=user_id,
            status_change_type_id=type_id,
            change_source_id=source_id,
            timestamp=datetime.utcnow(),
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by_user_id=changed_by_user_id
        )
        
        db.session.add(status_change)
        db.session.commit()
        
        return status_change
    except Exception as e:
        print(f"Error logging status change: {e}")
        db.session.rollback()
        return None


def log_account_created(user_id, source='user_action', changed_by_user_id=None):
    """Log when a new account is created."""
    return log_status_change(user_id, 'account_created', source, changed_by_user_id=changed_by_user_id)


def log_account_deleted(user_id, source='user_action', changed_by_user_id=None):
    """Log when an account is deleted."""
    return log_status_change(user_id, 'account_deleted', source, changed_by_user_id=changed_by_user_id)


def log_email_changed(user_id, old_email, new_email, source='user_action', changed_by_user_id=None):
    """Log when a user's email is changed."""
    return log_status_change(user_id, 'email_changed', source, old_email, new_email, changed_by_user_id=changed_by_user_id)


def log_subscription_changed(user_id, old_tier, new_tier, source='user_action', changed_by_user_id=None):
    """Log when a user's subscription tier is changed."""
    return log_status_change(user_id, 'subscription_tier_changed', source, old_tier, new_tier, changed_by_user_id=changed_by_user_id)


def log_test_flag_changed(user_id, old_value, new_value, source='admin_action', changed_by_user_id=None):
    """Log when a user's test flag is changed."""
    return log_status_change(user_id, 'test_flag_changed', source, old_value, new_value, changed_by_user_id=changed_by_user_id)


def log_password_changed(user_id, source='user_action', changed_by_user_id=None):
    """Log when a user's password is changed."""
    return log_status_change(user_id, 'password_changed', source, changed_by_user_id=changed_by_user_id)


def log_email_verified(user_id, source='user_action', changed_by_user_id=None):
    """Log when a user verifies their email."""
    return log_status_change(user_id, 'email_verified', source, changed_by_user_id=changed_by_user_id)


def log_google_connected(user_id, source='user_action', changed_by_user_id=None):
    """Log when a user connects their Google account."""
    return log_status_change(user_id, 'google_connected', source, changed_by_user_id=changed_by_user_id)


def log_google_disconnected(user_id, source='user_action', changed_by_user_id=None):
    """Log when a user disconnects their Google account."""
    return log_status_change(user_id, 'google_disconnected', source, changed_by_user_id=changed_by_user_id)


def log_fitbit_connected(user_id, source='user_action', changed_by_user_id=None):
    """Log when a user connects their Fitbit account."""
    return log_status_change(user_id, 'fitbit_connected', source, changed_by_user_id=changed_by_user_id)


def log_fitbit_disconnected(user_id, source='user_action', changed_by_user_id=None):
    """Log when a user disconnects their Fitbit account."""
    return log_status_change(user_id, 'fitbit_disconnected', source, changed_by_user_id=changed_by_user_id)
