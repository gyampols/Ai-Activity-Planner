"""
Activity and appointment management routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime as dt

from models import db, Activity, Appointment


activities_bp = Blueprint('activities', __name__)


@activities_bp.route('/log')
@login_required
def log():
    """Display user's activities and appointments."""
    activities = Activity.query.filter_by(user_id=current_user.id).all()
    appointments = Appointment.query.filter_by(user_id=current_user.id).order_by(Appointment.date.asc()).all()
    return render_template('log.html', activities=activities, appointments=appointments)


@activities_bp.route('/add_activity', methods=['POST'])
@login_required
def add_activity():
    """Add a new activity for the current user."""
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    duration = request.form.get('duration', '').strip()
    duration_unit = request.form.get('duration_unit', 'minutes')
    intensity = request.form.get('intensity', '').strip()
    dependencies = request.form.get('dependencies', '').strip()
    description = request.form.get('description', '').strip()
    preferred_time = request.form.get('preferred_time', '').strip()
    preferred_days = request.form.getlist('preferred_days')
    
    if not name:
        flash('Activity name is required!', 'error')
        return redirect(url_for('activities.log'))
    
    # Validate and convert duration
    duration_minutes = None
    if duration:
        try:
            duration_value = int(duration)
            if duration_value < 1:
                flash('Duration must be a positive number!', 'error')
                return redirect(url_for('activities.log'))
            # Convert to minutes if in hours
            duration_minutes = duration_value * 60 if duration_unit == 'hours' else duration_value
        except ValueError:
            flash('Duration must be a valid number!', 'error')
            return redirect(url_for('activities.log'))
    
    # Join preferred days with comma
    preferred_days_str = ','.join(preferred_days) if preferred_days else None
    
    activity = Activity(
        user_id=current_user.id,
        name=name[:100],
        location=location[:200] if location else None,
        duration_minutes=duration_minutes,
        intensity=intensity if intensity in ['Low', 'Medium', 'High', 'Very High'] else None,
        dependencies=dependencies[:500] if dependencies else None,
        description=description[:1000] if description else None,
        preferred_time=preferred_time if preferred_time else None,
        preferred_days=preferred_days_str
    )
    
    db.session.add(activity)
    db.session.commit()
    flash('Activity added successfully!', 'success')
    
    return redirect(url_for('activities.log'))


@activities_bp.route('/delete_activity/<int:activity_id>', methods=['POST'])
@login_required
def delete_activity(activity_id):
    """Delete an activity."""
    activity = Activity.query.get_or_404(activity_id)
    
    if activity.user_id != current_user.id:
        flash('Unauthorized action!', 'error')
        return redirect(url_for('activities.log'))
    
    db.session.delete(activity)
    db.session.commit()
    flash('Activity deleted successfully!', 'success')
    
    return redirect(url_for('activities.log'))


@activities_bp.route('/add_appointment', methods=['POST'])
@login_required
def add_appointment():
    """Add a new appointment/responsibility for the current user."""
    title = request.form.get('title', '').strip()
    appointment_type = request.form.get('appointment_type', '').strip()
    date_str = request.form.get('date', '').strip()
    time_str = request.form.get('time', '').strip()
    duration = request.form.get('duration_minutes', '').strip()
    duration_unit = request.form.get('duration_unit', 'minutes')
    description = request.form.get('description', '').strip()
    repeating_days = request.form.getlist('repeating_days')
    
    if not title or not date_str:
        flash('Title and date are required!', 'error')
        return redirect(url_for('activities.log'))
    
    # Parse date
    try:
        appointment_date = dt.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format!', 'error')
        return redirect(url_for('activities.log'))
    
    # Parse time if provided
    appointment_time = None
    if time_str:
        try:
            appointment_time = dt.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid time format!', 'error')
            return redirect(url_for('activities.log'))
    
    # Parse duration
    duration_minutes = None
    if duration:
        try:
            duration_value = int(duration)
            if duration_value < 1:
                flash('Duration must be a positive number!', 'error')
                return redirect(url_for('activities.log'))
            # Convert to minutes if in hours
            duration_minutes = duration_value * 60 if duration_unit == 'hours' else duration_value
        except ValueError:
            flash('Duration must be a valid number!', 'error')
            return redirect(url_for('activities.log'))
    
    # Join repeating days with comma
    repeating_days_str = ','.join(repeating_days) if repeating_days else None
    
    appointment = Appointment(
        user_id=current_user.id,
        title=title[:200],
        appointment_type=appointment_type if appointment_type else 'Other',
        date=appointment_date,
        time=appointment_time,
        duration_minutes=duration_minutes,
        description=description[:1000] if description else None,
        repeating_days=repeating_days_str
    )
    
    db.session.add(appointment)
    db.session.commit()
    flash('Appointment added successfully!', 'success')
    
    return redirect(url_for('activities.log'))


@activities_bp.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(appointment_id):
    """Delete an appointment."""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.user_id != current_user.id:
        flash('Unauthorized action!', 'error')
        return redirect(url_for('activities.log'))
    
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment deleted successfully!', 'success')
    
    return redirect(url_for('activities.log'))


@activities_bp.route('/edit_activity/<int:activity_id>', methods=['POST'])
@login_required
def edit_activity(activity_id):
    """Edit an existing activity."""
    activity = Activity.query.get_or_404(activity_id)
    
    if activity.user_id != current_user.id:
        flash('Unauthorized action!', 'error')
        return redirect(url_for('activities.log'))
    
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    duration = request.form.get('duration', '').strip()
    duration_unit = request.form.get('duration_unit', 'minutes')
    intensity = request.form.get('intensity', '').strip()
    dependencies = request.form.get('dependencies', '').strip()
    description = request.form.get('description', '').strip()
    preferred_time = request.form.get('preferred_time', '').strip()
    preferred_days = request.form.getlist('preferred_days')
    
    if not name:
        flash('Activity name is required!', 'error')
        return redirect(url_for('activities.log'))
    
    # Validate and convert duration
    duration_minutes = None
    if duration:
        try:
            duration_value = int(duration)
            if duration_value < 1:
                flash('Duration must be a positive number!', 'error')
                return redirect(url_for('activities.log'))
            # Convert to minutes if in hours
            duration_minutes = duration_value * 60 if duration_unit == 'hours' else duration_value
        except ValueError:
            flash('Duration must be a valid number!', 'error')
            return redirect(url_for('activities.log'))
    
    # Update activity fields
    activity.name = name[:100]
    activity.location = location[:200] if location else None
    activity.duration_minutes = duration_minutes
    activity.intensity = intensity if intensity in ['Low', 'Medium', 'High', 'Very High'] else None
    activity.dependencies = dependencies[:500] if dependencies else None
    activity.description = description[:1000] if description else None
    activity.preferred_time = preferred_time if preferred_time else None
    activity.preferred_days = ','.join(preferred_days) if preferred_days else None
    
    db.session.commit()
    flash('Activity updated successfully!', 'success')
    
    return redirect(url_for('activities.log'))


@activities_bp.route('/edit_appointment/<int:appointment_id>', methods=['POST'])
@login_required
def edit_appointment(appointment_id):
    """Edit an existing appointment."""
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.user_id != current_user.id:
        flash('Unauthorized action!', 'error')
        return redirect(url_for('activities.log'))
    
    title = request.form.get('title', '').strip()
    appointment_type = request.form.get('appointment_type', '').strip()
    date_str = request.form.get('date', '').strip()
    time_str = request.form.get('time', '').strip()
    duration = request.form.get('duration_minutes', '').strip()
    duration_unit = request.form.get('duration_unit', 'minutes')
    description = request.form.get('description', '').strip()
    repeating_days = request.form.getlist('repeating_days')
    
    if not title or not date_str:
        flash('Title and date are required!', 'error')
        return redirect(url_for('activities.log'))
    
    # Parse date
    try:
        appointment_date = dt.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format!', 'error')
        return redirect(url_for('activities.log'))
    
    # Parse time if provided
    appointment_time = None
    if time_str:
        try:
            appointment_time = dt.strptime(time_str, '%H:%M').time()
        except ValueError:
            flash('Invalid time format!', 'error')
            return redirect(url_for('activities.log'))
    
    # Parse duration
    duration_minutes = None
    if duration:
        try:
            duration_value = int(duration)
            if duration_value < 1:
                flash('Duration must be a positive number!', 'error')
                return redirect(url_for('activities.log'))
            # Convert to minutes if in hours
            duration_minutes = duration_value * 60 if duration_unit == 'hours' else duration_value
        except ValueError:
            flash('Duration must be a valid number!', 'error')
            return redirect(url_for('activities.log'))
    
    # Update appointment fields
    appointment.title = title[:200]
    appointment.appointment_type = appointment_type if appointment_type else 'Other'
    appointment.date = appointment_date
    appointment.time = appointment_time
    appointment.duration_minutes = duration_minutes
    appointment.description = description[:1000] if description else None
    appointment.repeating_days = ','.join(repeating_days) if repeating_days else None
    
    db.session.commit()
    flash('Appointment updated successfully!', 'success')
    
    return redirect(url_for('activities.log'))
