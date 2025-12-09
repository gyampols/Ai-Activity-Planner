# Authentication & Admin System Documentation

## Email Verification System

### Overview
All new user signups require email verification to prevent spam accounts. Admin-tier accounts are automatically verified.

### Features
- **Token-based verification**: Secure random tokens generated using `secrets.token_urlsafe(32)`
- **24-hour expiry**: Verification links expire after 24 hours for security
- **Auto-verify admins**: Admin accounts skip verification (email confirmed by admin setup)
- **Google OAuth auto-verify**: Users signing up via Google are automatically verified
- **Grandfather clause**: Existing users are marked as verified during migration

### User Flow
1. User signs up with email and password
2. System generates verification token with 24-hour expiry
3. Email sent to user with verification link (currently logs to console)
4. User clicks link and verifies email
5. Account is activated and user can log in

### Routes
- `POST /signup` - Creates account and sends verification email
- `GET /verify_email?token=<token>` - Verifies email with token
- `GET /resend_verification` - Shows resend form
- `POST /resend_verification` - Resends verification email

### Database Fields
```python
email_verified = db.Column(db.Boolean, default=False, nullable=False)
verification_token = db.Column(db.String(255), nullable=True)
verification_token_expiry = db.Column(db.DateTime, nullable=True)
```

### Templates
- `templates/resend_verification.html` - Form to request new verification email

---

## Password Recovery System

### Overview
Users who forget their password can request a password reset link via email.

### Features
- **Token-based reset**: Secure random tokens with 1-hour expiry
- **Short expiry window**: Reset links expire after 1 hour for enhanced security
- **Email lookup**: Only valid emails receive reset links (prevents enumeration)
- **Password validation**: Minimum 6 characters required

### User Flow
1. User clicks "Forgot Password?" on login page
2. Enters email address
3. System generates reset token with 1-hour expiry
4. Email sent with reset link (currently logs to console)
5. User clicks link and enters new password
6. Password updated and token invalidated

### Routes
- `GET /forgot_password` - Shows password reset request form
- `POST /forgot_password` - Sends password reset email
- `GET /reset_password?token=<token>` - Shows password reset form
- `POST /reset_password` - Updates password with token validation

### Database Fields
```python
reset_token = db.Column(db.String(255), nullable=True)
reset_token_expiry = db.Column(db.DateTime, nullable=True)
```

### Templates
- `templates/forgot_password.html` - Request password reset form
- `templates/reset_password.html` - New password entry form

---

## Admin Panel Features

### User Management Table
The admin panel displays comprehensive user information:

| Column | Description |
|--------|-------------|
| ID | User database ID |
| Username | User's username |
| Email | User's email address |
| Tier | Subscription tier badge (Free/Paid/Admin) |
| Test | Checkbox to toggle test account status |
| Verified | Email verification status (✓ or ✗) |
| Generations | Usage count vs limit |
| Integrations | Connected services (Google, Fitbit, Oura) |
| Created | Account creation date |
| Actions | Management buttons |

### Test Flag Feature

#### Purpose
Mark specific accounts as test accounts for development/QA purposes.

#### Usage
- Admins can toggle the test flag for any user (except gregyampolsky)
- Checkbox in the "Test" column toggles via AJAX
- Visual feedback on toggle (row briefly highlights green)
- Protected accounts show disabled checkbox

#### Implementation
- **Database Field**: `test_flag = db.Column(db.Boolean, default=False)`
- **Endpoint**: `POST /admin/toggle_test_flag`
- **Returns**: `{'success': true, 'test_flag': bool}`
- **JavaScript**: `toggleTestFlag(userId, checkbox)` function

### Email Change Feature

#### Purpose
Allow admins to correct or update user email addresses without requiring verification.

#### Features
- Admin changes bypass email verification
- Validates email format and uniqueness
- Protected from gregyampolsky account modifications
- Modal interface for easy updates

#### Usage
1. Click "Change Email" button in Actions column
2. Modal displays current email
3. Enter new email address
4. Submit to update (no verification required)

#### Implementation
- **Endpoint**: `POST /admin/update_user_email`
- **Parameters**: `user_id`, `new_email`
- **Validation**: Email format, uniqueness check, gregyampolsky protection
- **JavaScript**: `showChangeEmailModal(userId, username, currentEmail)`

### Subscription Tier Management

#### Tiers
- **Free Tier**: 3 plan generations per week
- **Paid Tier**: 20 plan generations per week, calendar import/export
- **Admin**: Unlimited generations, full admin panel access

#### Features
- Change any user's tier (except gregyampolsky)
- Visual tier badges with icons
- Usage tracking per tier
- Rate limiting enforcement

### User Deletion
- Permanently delete user accounts
- Removes all associated data (activities, appointments, integrations)
- Protected from deleting gregyampolsky account
- Confirmation modal with warning

---

## Security Features

### Protected Account: gregyampolsky

The admin account is protected at multiple layers:

1. **Tier changes**: Cannot modify subscription tier
2. **Email changes**: Cannot change email address
3. **Test flag**: Cannot toggle test flag
4. **Deletion**: Cannot delete account
5. **UI indication**: Shows "🔒 Protected" instead of action buttons

Protection checks include both:
- Username: `gregyampolsky` (case-insensitive)
- Email: `gregyampolsky@gmail.com` (case-insensitive)

### CSRF Protection
- All forms include CSRF tokens
- AJAX endpoints validate CSRF in headers
- Uses Flask-WTF for token generation

### Token Security
- **Verification tokens**: 24-hour expiry, 32-byte random
- **Reset tokens**: 1-hour expiry, 32-byte random
- **Generation**: `secrets.token_urlsafe(32)`
- **Validation**: Check expiry before accepting

---

## Email System (Placeholder)

### Current Implementation
Emails are currently logged to the console for development:

```python
print(f"===== EMAIL TO SEND =====")
print(f"To: {user.email}")
print(f"Subject: ...")
print(f"Verification URL: {verification_url}")
print(f"========================")
```

### Production Setup
To enable actual email sending:

1. **Choose email service**: SendGrid, AWS SES, or SMTP
2. **Update `utils/email.py`**: Replace console logging with actual email sending
3. **Add configuration**: Email credentials in `config.py` or environment variables
4. **Test**: Send test emails before production deployment

### Example SendGrid Implementation
```python
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

def send_verification_email(user, app_url):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
    from_email = Email("noreply@yourdomain.com")
    to_email = To(user.email)
    subject = "Verify your email address"
    content = Content("text/html", f"<p>Click here to verify: {verification_url}</p>")
    mail = Mail(from_email, to_email, subject, content)
    response = sg.client.mail.send.post(request_body=mail.get())
```

---

## Database Migrations

### Migration 3: Authentication Fields
Adds all authentication and admin fields to the User table:

```sql
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS test_flag BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS verification_token_expiry TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP;

-- Grandfather existing users as verified
UPDATE "user" SET email_verified = TRUE WHERE email_verified = FALSE AND created_at < NOW();
```

### Running Migrations
Migrations run automatically on app startup via `app.py`:
```python
run_migrations(db)
```

---

## Testing Checklist

### Email Verification
- [ ] New signup sends verification email
- [ ] Unverified users cannot log in
- [ ] Verification link activates account
- [ ] Expired tokens are rejected
- [ ] Admin accounts skip verification
- [ ] Google OAuth users auto-verified
- [ ] Can resend verification email

### Password Recovery
- [ ] Forgot password sends reset email
- [ ] Reset link works within 1 hour
- [ ] Expired tokens rejected
- [ ] Password successfully updated
- [ ] Old password no longer works
- [ ] Invalid emails don't reveal user existence

### Admin Panel
- [ ] Test flag toggles correctly
- [ ] Test flag protected for gregyampolsky
- [ ] Email change updates successfully
- [ ] Email change validates format
- [ ] Email change checks uniqueness
- [ ] Email change protected for gregyampolsky
- [ ] Tier changes work (except gregyampolsky)
- [ ] User deletion works (except gregyampolsky)
- [ ] All buttons disabled for gregyampolsky

### Security
- [ ] CSRF tokens validated
- [ ] Tokens are securely random
- [ ] Token expiry enforced
- [ ] gregyampolsky account fully protected
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (Jinja2 auto-escaping)

---

## File Structure

```
Ai-Activity-Planner/
├── utils/
│   └── email.py              # Email sending utilities
├── routes/
│   ├── auth.py              # Authentication routes
│   └── admin.py             # Admin panel routes
├── templates/
│   ├── forgot_password.html # Password reset request
│   ├── reset_password.html  # Password reset form
│   ├── resend_verification.html # Resend verification
│   ├── login.html           # Login (updated with links)
│   └── admin.html           # Admin panel (updated)
├── models.py                # User model with new fields
└── app.py                   # Migration 3 implementation
```

---

## Configuration

### Environment Variables (Future)
```bash
# Email service
SENDGRID_API_KEY=your_api_key
EMAIL_FROM=noreply@yourdomain.com

# Or for AWS SES
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

### Flask Config
```python
# config.py
MAIL_SERVER = 'smtp.sendgrid.net'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'apikey'
MAIL_PASSWORD = os.environ.get('SENDGRID_API_KEY')
```

---

## Future Enhancements

### Email System
- [ ] Integrate SendGrid or AWS SES
- [ ] HTML email templates
- [ ] Email tracking and analytics
- [ ] Bounce handling
- [ ] Unsubscribe functionality

### Admin Features
- [ ] User search and filtering
- [ ] Bulk operations
- [ ] Activity logs (audit trail)
- [ ] Export user data
- [ ] Advanced analytics dashboard

### Authentication
- [ ] Two-factor authentication (2FA)
- [ ] Remember me functionality
- [ ] Session management
- [ ] Login history
- [ ] Suspicious activity detection

### Test Accounts
- [ ] Separate test data from production
- [ ] Auto-cleanup of test accounts
- [ ] Test mode toggle
- [ ] Seeded test data

---

## Support

For questions or issues with the authentication system:
1. Check console logs for email verification URLs (development)
2. Verify database migrations ran successfully
3. Check that user has correct `email_verified` status
4. Ensure tokens haven't expired
5. Review CSRF token validation

For admin panel issues:
1. Verify user has `subscription_tier='admin'`
2. Check that JavaScript functions are loading
3. Verify CSRF tokens in AJAX calls
4. Check browser console for errors
5. Ensure gregyampolsky protection is working
