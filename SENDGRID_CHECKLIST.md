# SendGrid Setup Checklist

## ✅ Completed
- [x] SendGrid account created
- [x] API Key created and saved to .env
- [x] EMAIL_FROM set to gregyampolsky@gmail.com
- [x] Deploying to Cloud Run with environment variables

## 🔄 You Need To Do Now

### 1. Verify Sender Email (REQUIRED!)
**Go to:** https://app.sendgrid.com/settings/sender_auth

**Steps:**
1. Click "Verify a Single Sender"
2. Click "Create New Sender" (if needed)
3. Fill in the form:
   - From Email: gregyampolsky@gmail.com
   - From Name: AI Activity Planner
   - Reply To: gregyampolsky@gmail.com
4. Click "Create"
5. **CHECK YOUR GMAIL** for verification email
6. Click "Verify Single Sender" button in the email
7. Confirm you see green checkmark ✓ in SendGrid dashboard

**Without this step, emails will NOT send!**

---

## 🧪 After Verification, Test It!

### Test 1: Email Verification
1. Go to your app
2. Sign up with a NEW email (not gregyampolsky@gmail.com)
3. Check that email's inbox
4. You should receive: "Verify Your Email - AI Activity Planner"
5. Beautiful HTML email with verification button

### Test 2: Password Reset
1. Go to login page
2. Click "Forgot Password?"
3. Enter your test email
4. Check inbox
5. You should receive: "Reset Your Password - AI Activity Planner"

---

## 📊 Monitor Email Activity

**SendGrid Dashboard:**
- Go to: https://app.sendgrid.com/
- Click "Activity" in left sidebar
- See all emails sent, delivered, opened
- Check for any errors or bounces

**Cloud Run Logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-activity-planner" --limit 20
```

Look for:
- ✅ "Email sent successfully to..."
- ❌ "Error sending email..."

---

## 🆘 Troubleshooting

### Emails not sending?

1. **Check sender verification:**
   - Go to SendGrid → Settings → Sender Authentication
   - gregyampolsky@gmail.com should have green ✓
   - Status should say "Verified"

2. **Check Cloud Run logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" --limit 50 | grep -i email
   ```

3. **Check SendGrid Activity:**
   - https://app.sendgrid.com/activity
   - Should show sent emails
   - If showing errors, check what they say

4. **Check API Key:**
   - Make sure it starts with "SG."
   - Verify it has "Mail Send" permissions
   - Try creating a new one if needed

### Common Errors:

- **"Sender not verified"** → Complete sender verification above
- **"403 Forbidden"** → API key doesn't have Mail Send permission
- **Emails in spam** → Normal for first sends, will improve
- **"Invalid API key"** → Double-check you copied it correctly

---

## ✅ Success Indicators

You'll know it's working when:
- ✓ Green checkmark next to gregyampolsky@gmail.com in SendGrid
- ✓ New signups receive verification emails
- ✓ Password reset emails arrive
- ✓ Emails are beautifully formatted (HTML)
- ✓ SendGrid Activity shows "Delivered" status
- ✓ Cloud Run logs show "Email sent successfully"

---

## 📝 Notes

- Free tier: 100 emails/day (should be plenty!)
- Emails from new domains might go to spam initially
- Check SendGrid reputation dashboard if issues
- Consider domain authentication for production (more advanced)

**Current Status:**
- API Key: Configured ✓
- Email From: gregyampolsky@gmail.com
- Deployment: In progress...
- Sender Verification: **YOU NEED TO COMPLETE THIS!**
