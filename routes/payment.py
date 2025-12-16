"""
Payment routes for Stripe subscription management.
"""
from datetime import datetime

import stripe
from flask import Blueprint, request, jsonify, redirect, url_for, flash, render_template
from flask_login import login_required, current_user

from config import config
from models import db, User, Transaction
from utils.status_logger import log_subscription_changed

payment_bp = Blueprint('payment', __name__)

stripe.api_key = config.STRIPE_SECRET_KEY


@payment_bp.route('/upgrade')
@login_required
def upgrade_page():
    """Show the upgrade page with pricing information."""
    # Check if user has already paid before
    if current_user.has_paid_before:
        # User has paid before, can upgrade for free
        return render_template('upgrade.html', 
                               has_paid_before=True,
                               stripe_key=config.STRIPE_PUBLISHABLE_KEY)
    else:
        return render_template('upgrade.html', 
                               has_paid_before=False,
                               stripe_key=config.STRIPE_PUBLISHABLE_KEY)


@payment_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session for subscription upgrade."""
    if not config.STRIPE_SECRET_KEY or not config.STRIPE_PRICE_ID:
        flash('Payment system is not configured. Please contact support.', 'danger')
        return redirect(url_for('main.settings'))
    
    # Check if user has already paid - they can upgrade for free
    if current_user.has_paid_before:
        # Upgrade immediately without payment
        old_tier = current_user.subscription_tier
        current_user.subscription_tier = 'paid_tier'
        current_user.plan_generations_count = 0
        db.session.commit()
        
        # Log the status change
        log_subscription_changed(current_user.id, old_tier, 'paid_tier', source='user_action')
        
        flash('Successfully upgraded to Paid Tier!', 'success')
        return redirect(url_for('main.settings'))
    
    # Check if already paid tier
    if current_user.subscription_tier == 'paid_tier':
        flash('You are already on the paid tier.', 'info')
        return redirect(url_for('main.settings'))
    
    if current_user.subscription_tier == 'admin':
        flash('Admin accounts have full access.', 'info')
        return redirect(url_for('main.settings'))
    
    try:
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': config.STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='payment',  # One-time payment for lifetime access
            success_url=f"{config.BASE_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{config.BASE_URL}/payment/cancel",
            customer_email=current_user.email,
            metadata={
                'user_id': current_user.id,
                'username': current_user.username
            }
        )
        
        # Create a pending transaction record
        transaction = Transaction(
            user_id=current_user.id,
            stripe_session_id=checkout_session.id,
            amount_cents=0,  # Will be updated on completion
            transaction_type='subscription_upgrade',
            status='pending',
            description='Upgrade to Paid Tier'
        )
        db.session.add(transaction)
        db.session.commit()
        
        return redirect(checkout_session.url)
        
    except stripe.error.StripeError as e:
        flash(f'Payment error: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))


@payment_bp.route('/payment/success')
def payment_success():
    """Handle successful payment callback."""
    session_id = request.args.get('session_id')
    
    if not session_id:
        flash('Invalid payment session.', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        # Retrieve the session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Get user from session metadata (works even if not logged in)
        user_id = checkout_session.metadata.get('user_id')
        if not user_id:
            flash('Invalid payment session.', 'danger')
            return redirect(url_for('auth.login'))
        
        user = User.query.get(int(user_id))
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check payment status
        if checkout_session.payment_status == 'paid':
            # Update transaction record
            transaction = Transaction.query.filter_by(stripe_session_id=session_id).first()
            if transaction:
                transaction.status = 'completed'
                transaction.amount_cents = checkout_session.amount_total or 0
                transaction.stripe_payment_intent_id = checkout_session.payment_intent
                transaction.completed_at = datetime.utcnow()
            
            # Update user tier
            old_tier = user.subscription_tier
            user.subscription_tier = 'paid_tier'
            user.has_paid_before = True
            user.plan_generations_count = 0
            
            db.session.commit()
            
            # Log the status change
            log_subscription_changed(user.id, old_tier, 'paid_tier', source='user_action')
            
            # Check if user is logged in
            if current_user.is_authenticated and current_user.id == user.id:
                flash('🎉 Payment successful! Welcome to the Paid Tier!', 'success')
                return redirect(url_for('main.settings'))
            else:
                # User session was lost, show success and prompt to login
                flash('🎉 Payment successful! Please log in to access your Paid Tier features.', 'success')
                return redirect(url_for('auth.login'))
        else:
            flash('Payment was not completed. Please try again.', 'warning')
            return redirect(url_for('auth.login'))
        
    except stripe.error.StripeError as e:
        flash(f'Error verifying payment: {str(e)}', 'danger')
        return redirect(url_for('main.settings'))


@payment_bp.route('/payment/cancel')
def payment_cancel():
    """Handle cancelled payment."""
    flash('Payment was cancelled.', 'info')
    if current_user.is_authenticated:
        return redirect(url_for('main.settings'))
    else:
        return redirect(url_for('auth.login'))


@payment_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    if not config.STRIPE_WEBHOOK_SECRET:
        # Webhook secret not configured, process without verification (development)
        try:
            event = stripe.Event.construct_from(
                request.get_json(), stripe.api_key
            )
        except ValueError:
            return jsonify({'error': 'Invalid payload'}), 400
    else:
        # Verify webhook signature (production)
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, config.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return jsonify({'error': 'Invalid payload'}), 400
        except stripe.error.SignatureVerificationError:
            return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_succeeded(payment_intent)
    
    return jsonify({'status': 'success'}), 200


def handle_checkout_completed(session):
    """Handle successful checkout session completion."""
    user_id = session.get('metadata', {}).get('user_id')
    
    if not user_id:
        print(f"Webhook: No user_id in session metadata")
        return
    
    user = User.query.get(int(user_id))
    if not user:
        print(f"Webhook: User {user_id} not found")
        return
    
    # Update transaction
    transaction = Transaction.query.filter_by(stripe_session_id=session['id']).first()
    if transaction:
        transaction.status = 'completed'
        transaction.amount_cents = session.get('amount_total', 0)
        transaction.stripe_payment_intent_id = session.get('payment_intent')
        transaction.completed_at = datetime.utcnow()
    
    # Update user tier
    old_tier = user.subscription_tier
    user.subscription_tier = 'paid_tier'
    user.has_paid_before = True
    user.plan_generations_count = 0
    
    db.session.commit()
    
    # Log the status change
    log_subscription_changed(user.id, old_tier, 'paid_tier', source='system_automatic')
    
    print(f"Webhook: User {user.username} upgraded to paid_tier via Stripe")


def handle_payment_succeeded(payment_intent):
    """Handle successful payment intent."""
    # Find transaction by payment intent ID
    transaction = Transaction.query.filter_by(
        stripe_payment_intent_id=payment_intent['id']
    ).first()
    
    if transaction and transaction.status != 'completed':
        transaction.status = 'completed'
        transaction.completed_at = datetime.utcnow()
        db.session.commit()


@payment_bp.route('/downgrade', methods=['POST'])
@login_required
def downgrade():
    """Downgrade from paid tier to free tier."""
    if current_user.subscription_tier == 'admin':
        flash('Admin accounts cannot be downgraded.', 'warning')
        return redirect(url_for('main.settings'))
    
    if current_user.subscription_tier == 'free_tier':
        flash('You are already on the free tier.', 'info')
        return redirect(url_for('main.settings'))
    
    old_tier = current_user.subscription_tier
    current_user.subscription_tier = 'free_tier'
    current_user.plan_generations_count = 0
    db.session.commit()
    
    # Log the status change
    log_subscription_changed(current_user.id, old_tier, 'free_tier', source='user_action')
    
    flash('Successfully downgraded to Free Tier. You can upgrade again anytime without paying!', 'success')
    return redirect(url_for('main.settings'))


@payment_bp.route('/free-upgrade', methods=['POST'])
@login_required
def free_upgrade():
    """Free upgrade for users who have previously paid."""
    if not current_user.has_paid_before:
        flash('You need to purchase the paid tier first.', 'warning')
        return redirect(url_for('payment.upgrade_page'))
    
    if current_user.subscription_tier == 'paid_tier':
        flash('You are already on the paid tier.', 'info')
        return redirect(url_for('main.settings'))
    
    if current_user.subscription_tier == 'admin':
        flash('Admin accounts have full access.', 'info')
        return redirect(url_for('main.settings'))
    
    old_tier = current_user.subscription_tier
    current_user.subscription_tier = 'paid_tier'
    current_user.plan_generations_count = 0
    db.session.commit()
    
    # Log the status change
    log_subscription_changed(current_user.id, old_tier, 'paid_tier', source='user_action')
    
    flash('Successfully upgraded to Paid Tier!', 'success')
    return redirect(url_for('main.settings'))
