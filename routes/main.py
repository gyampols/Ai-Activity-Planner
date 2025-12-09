"""
Main routes for basic pages and utility endpoints.
"""
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user, logout_user

from models import db
from utils.helpers import search_cities


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')


@main_bp.route('/terms')
def terms():
    """Terms of Service page."""
    return render_template('terms.html')


@main_bp.route('/privacy')
def privacy():
    """Privacy Policy page."""
    return render_template('privacy.html')


@main_bp.route('/search_cities')
@login_required
def search_cities_route():
    """Search for cities matching a query."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])
    
    cities = search_cities(query)
    return jsonify(cities)


@main_bp.route('/toggle_temperature_unit', methods=['POST'])
@login_required
def toggle_temperature_unit():
    """Toggle user's temperature unit preference between C and F."""
    current_unit = current_user.temperature_unit or 'C'
    new_unit = 'F' if current_unit == 'C' else 'C'
    current_user.temperature_unit = new_unit
    db.session.commit()
    return jsonify({'unit': new_unit})


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page for profile management."""
    if request.method == 'POST':
        try:
            # Update profile fields
            current_user.full_name = request.form.get('full_name', '').strip() or None
            current_user.location = request.form.get('location', '').strip() or None
            current_user.temperature_unit = request.form.get('temperature_unit', 'C')
            current_user.timezone = request.form.get('timezone', 'UTC')
            
            # Update age (with validation)
            age_str = request.form.get('age', '').strip()
            if age_str:
                age = int(age_str)
                if age < 13 or age > 120:
                    flash('Age must be between 13 and 120.', 'danger')
                    return redirect(url_for('main.settings'))
                current_user.age = age
            else:
                current_user.age = None
            
            # Update gender
            current_user.gender = request.form.get('gender', '').strip() or None
            
            # Update height (with validation)
            height_str = request.form.get('height_cm', '').strip()
            if height_str:
                height = int(height_str)
                if height < 50 or height > 300:
                    flash('Height must be between 50 and 300 cm.', 'danger')
                    return redirect(url_for('main.settings'))
                current_user.height_cm = height
            else:
                current_user.height_cm = None
            
            # Update weight (with validation)
            weight_str = request.form.get('weight_kg', '').strip()
            if weight_str:
                weight = float(weight_str)
                if weight < 20 or weight > 500:
                    flash('Weight must be between 20 and 500 kg.', 'danger')
                    return redirect(url_for('main.settings'))
                current_user.weight_kg = weight
            else:
                current_user.weight_kg = None
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('main.settings'))
        
        except ValueError:
            flash('Invalid input. Please check your age, height, and weight values.', 'danger')
            return redirect(url_for('main.settings'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            return redirect(url_for('main.settings'))
    
    return render_template('settings.html')


@main_bp.route('/update_subscription', methods=['POST'])
@login_required
def update_subscription():
    """Update user's subscription tier."""
    try:
        new_tier = request.form.get('new_tier', '').strip()
        
        # Validate tier
        valid_tiers = ['free_tier', 'paid_tier']
        if new_tier not in valid_tiers:
            flash('Invalid subscription tier.', 'danger')
            return redirect(url_for('main.settings'))
        
        # Prevent users from setting themselves to admin
        if current_user.subscription_tier != 'admin' and new_tier not in valid_tiers:
            flash('You cannot change to admin tier.', 'danger')
            return redirect(url_for('main.settings'))
        
        # Admin users cannot downgrade themselves
        if current_user.subscription_tier == 'admin':
            flash('Admin accounts cannot change subscription tiers.', 'danger')
            return redirect(url_for('main.settings'))
        
        old_tier = current_user.subscription_tier
        current_user.subscription_tier = new_tier
        
        # Reset generation count when upgrading
        if new_tier == 'paid_tier' and old_tier == 'free_tier':
            current_user.plan_generations_count = 0
        
        db.session.commit()
        
        if new_tier == 'paid_tier':
            flash('Successfully upgraded to Paid Plan! You now have 20 generations per week.', 'success')
        else:
            flash('Successfully changed to Free Plan. You now have 3 generations per week.', 'success')
        
        return redirect(url_for('main.settings'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating subscription: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))


@main_bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data."""
    try:
        user = current_user
        
        # Log out the user
        logout_user()
        
        # Delete the user (cascade will delete activities and appointments)
        db.session.delete(user)
        db.session.commit()
        
        flash('Your account has been deleted successfully.', 'success')
        return redirect(url_for('main.index'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting account: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))


@main_bp.route('/version')
def version():
    """Show current version info to verify deployment."""
    import os
    return jsonify({
        'version': '2.0-modular',
        'build_number': os.environ.get('BUILD_NUM', 'unknown'),
        'features': [
            'Modular architecture with blueprints',
            'Fixed checkbox alignment', 
            'Repeating appointments',
            'CircleCI auto-deployment'
        ],
        'deployed': True,
        'environment': 'production' if not os.environ.get('FLASK_DEBUG') else 'development',
        'app_module': __name__
    })
