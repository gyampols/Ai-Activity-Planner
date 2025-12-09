# Email Configuration Guide

## SendGrid Setup

The application now uses SendGrid for sending emails (verification, password reset).

### 1. Create SendGrid Account

1. Go to [sendgrid.com](https://sendgrid.com)
2. Sign up for a free account (100 emails/day free forever)
3. Verify your email address

### 2. Create API Key

1. Log into SendGrid dashboard
2. Go to **Settings** → **API Keys**
3. Click **Create API Key**
4. Name it (e.g., "AI Activity Planner")
5. Select **Full Access** or **Restricted Access** with Mail Send permissions
6. Click **Create & View**
7. **COPY THE API KEY** (you won't be able to see it again!)

### 3. Verify Sender Identity

SendGrid requires sender verification to prevent spam:

1. Go to **Settings** → **Sender Authentication**
2. Choose one of:
   - **Single Sender Verification** (easier, good for testing)
   - **Domain Authentication** (better for production)

#### Single Sender Verification:
1. Click **Verify a Single Sender**
2. Fill in your details:
   - From Name: "AI Activity Planner"
   - From Email: your verified email (e.g., noreply@yourdomain.com)
   - Reply To: your support email
3. Check your email and verify
4. Use this email as `EMAIL_FROM` environment variable

### 4. Configure Environment Variables

Add these to your Cloud Run environment:

```bash
SENDGRID_API_KEY=your_sendgrid_api_key_here
EMAIL_FROM=noreply@yourdomain.com  # Must be verified in SendGrid
```

### 5. Deploy to Cloud Run with Environment Variables

Option A - Using gcloud command:
```bash
gcloud run deploy ai-activity-planner \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "SENDGRID_API_KEY=your_key_here,EMAIL_FROM=noreply@yourdomain.com"
```

Option B - Using Cloud Console:
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click on your service: `ai-activity-planner`
3. Click **Edit & Deploy New Revision**
4. Go to **Variables & Secrets** tab
5. Add environment variables:
   - Name: `SENDGRID_API_KEY`, Value: your API key
   - Name: `EMAIL_FROM`, Value: your verified email
6. Click **Deploy**

### 6. Test Email Sending

After deployment:

1. Sign up for a new account
2. Check your email for verification link
3. Click "Forgot Password?" to test password reset
4. Check Cloud Run logs if emails aren't being sent:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-activity-planner" --limit 50 --format json
   ```

## Fallback Behavior

If `SENDGRID_API_KEY` is not set, the app will:
- Still work normally
- Log email content to console (visible in Cloud Run logs)
- Show success messages to users
- Useful for development and testing

## Email Templates

The application sends HTML emails with:
- Professional styling
- Gradient headers
- Clear call-to-action buttons
- Fallback plain text links
- Expiry warnings
- Security notices

### Verification Email
- Subject: "Verify Your Email - AI Activity Planner"
- Expires: 24 hours
- Includes: Verification link + manual URL

### Password Reset Email
- Subject: "Reset Your Password - AI Activity Planner"
- Expires: 1 hour
- Includes: Reset link + security warning

## Troubleshooting

### Emails not sending
1. Check SendGrid API key is correct
2. Verify sender email in SendGrid dashboard
3. Check Cloud Run logs for errors
4. Ensure EMAIL_FROM matches verified sender

### "Sender not verified" error
- Go to SendGrid → Settings → Sender Authentication
- Verify your sender email address
- Wait a few minutes for verification to propagate

### Rate limits
- Free tier: 100 emails/day
- If you hit limits, upgrade plan or implement email queuing
- Check SendGrid dashboard for usage stats

### Testing in development
- Set SENDGRID_API_KEY in `.env` file
- Or leave unset to see console output only
- Use real email addresses for testing verification

## Production Best Practices

1. **Use Domain Authentication** instead of Single Sender
2. **Monitor SendGrid dashboard** for delivery rates
3. **Set up email templates** in SendGrid for consistency
4. **Implement retry logic** for failed sends
5. **Add unsubscribe links** for marketing emails
6. **Monitor bounce rates** and remove invalid emails
7. **Use dedicated IP** for high-volume sending (paid plans)

## Cost

- **Free**: 100 emails/day forever
- **Essentials**: $19.95/mo for 50k emails/month
- **Pro**: $89.95/mo for 100k emails/month

For most applications, the free tier is sufficient!

## Alternative Email Services

If you prefer not to use SendGrid, you can modify `utils/email.py` to use:

- **AWS SES** (Simple Email Service)
- **Mailgun**
- **Postmark**
- **SMTP** (any provider)

The `send_email()` function is centralized for easy replacement.
