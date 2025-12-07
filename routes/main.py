"""
Main routes for basic pages and utility endpoints.
"""
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user

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


@main_bp.route('/version')
def version():
    """Show current version info to verify deployment."""
    import os
    return jsonify({
        'version': '2.0-modular',
        'features': [
            'Modular architecture with blueprints',
            'Fixed checkbox alignment', 
            'Repeating appointments',
            'CircleCI auto-deployment'
        ],
        'deployed': True,
        'environment': 'production' if not os.environ.get('FLASK_DEBUG') else 'development'
    })
