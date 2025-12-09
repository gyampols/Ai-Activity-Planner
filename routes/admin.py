"""
Admin routes for user management.
"""
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User
from datetime import datetime


admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.subscription_tier != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    """Admin panel for managing users."""
    # Get all users sorted by creation date
    users = User.query.order_by(User.created_at.desc()).all()
    
    # Calculate stats
    total_users = len(users)
    free_users = sum(1 for u in users if (u.subscription_tier or 'free_tier') == 'free_tier')
    paid_users = sum(1 for u in users if (u.subscription_tier or 'free_tier') == 'paid_tier')
    admin_users = sum(1 for u in users if (u.subscription_tier or 'free_tier') == 'admin')
    
    stats = {
        'total': total_users,
        'free': free_users,
        'paid': paid_users,
        'admin': admin_users
    }
    
    return render_template('admin.html', users=users, stats=stats)


@admin_bp.route('/admin/update_user_tier', methods=['POST'])
@login_required
@admin_required
def update_user_tier():
    """Update a user's subscription tier."""
    try:
        user_id = request.form.get('user_id')
        new_tier = request.form.get('new_tier')
        
        if not user_id or not new_tier:
            flash('Missing user ID or tier.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Validate tier
        valid_tiers = ['free_tier', 'paid_tier', 'admin']
        if new_tier not in valid_tiers:
            flash('Invalid subscription tier.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        user = User.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Prevent admin from changing their own tier
        if user.id == current_user.id:
            flash('You cannot change your own subscription tier.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Prevent changing gregyampolsky account tier
        if user.username.lower() == 'gregyampolsky' or user.email.lower() == 'gregyampolsky@gmail.com':
            flash('The gregyampolsky account tier cannot be changed.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        old_tier = user.subscription_tier or 'free_tier'
        user.subscription_tier = new_tier
        
        # Reset generation count when changing tiers
        user.plan_generations_count = 0
        
        db.session.commit()
        
        flash(f'Successfully changed {user.username}\'s subscription from {old_tier} to {new_tier}.', 'success')
        return redirect(url_for('admin.admin_panel'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user tier: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/admin/delete_user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    """Delete a user account."""
    try:
        user_id = request.form.get('user_id')
        
        if not user_id:
            flash('Missing user ID.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        user = User.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            flash('You cannot delete your own account from the admin panel.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Prevent deleting gregyampolsky account
        if user.username.lower() == 'gregyampolsky' or user.email.lower() == 'gregyampolsky@gmail.com':
            flash('The gregyampolsky account cannot be deleted.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Successfully deleted user {username}.', 'success')
        return redirect(url_for('admin.admin_panel'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/admin/toggle_test_flag', methods=['POST'])
@login_required
@admin_required
def toggle_test_flag():
    """Toggle a user's test flag."""
    try:
        user_id = request.form.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user ID'}), 400
        
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Prevent changing gregyampolsky account
        if user.username.lower() == 'gregyampolsky' or user.email.lower() == 'gregyampolsky@gmail.com':
            return jsonify({'success': False, 'error': 'Cannot modify gregyampolsky account'}), 403
        
        # Toggle test flag
        user.test_flag = not user.test_flag
        db.session.commit()
        
        return jsonify({'success': True, 'test_flag': user.test_flag})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/admin/update_user_email', methods=['POST'])
@login_required
@admin_required
def update_user_email():
    """Update a user's email address."""
    try:
        user_id = request.form.get('user_id')
        new_email = request.form.get('new_email', '').strip()
        
        if not user_id or not new_email:
            flash('Missing user ID or email.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Validate email format
        if '@' not in new_email or len(new_email) > 120:
            flash('Invalid email format.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        user = User.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Prevent changing gregyampolsky account
        if user.username.lower() == 'gregyampolsky' or user.email.lower() == 'gregyampolsky@gmail.com':
            flash('Cannot modify gregyampolsky account email.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user and existing_user.id != user.id:
            flash('This email is already in use by another account.', 'danger')
            return redirect(url_for('admin.admin_panel'))
        
        old_email = user.email
        user.email = new_email
        user.email_verified = True  # Admin changes don't require verification
        db.session.commit()
        
        flash(f'Successfully changed {user.username}\'s email from {old_email} to {new_email}.', 'success')
        return redirect(url_for('admin.admin_panel'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating email: {str(e)}', 'danger')
        return redirect(url_for('admin.admin_panel'))
