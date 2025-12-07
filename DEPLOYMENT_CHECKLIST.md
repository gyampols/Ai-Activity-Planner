# Deployment Checklist

## ✅ Completed
- [x] User settings page with profile management
- [x] Terms of Service page
- [x] Privacy Policy page
- [x] Database schema updated with new user fields
- [x] Database migration script created
- [x] Footer with Terms/Privacy links
- [x] Settings link in navbar
- [x] Delete account functionality
- [x] Data persistence documentation

## 🔄 Required Before Production Deployment

### 1. Google OAuth Console Configuration (CRITICAL)
**Why:** Required for Google OAuth to work and for app verification

**Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to: APIs & Services → OAuth consent screen
3. Add **Terms of Service URL**: `https://ai-activity-planner-mola55j5ra-uc.a.run.app/terms`
4. Add **Privacy Policy URL**: `https://ai-activity-planner-mola55j5ra-uc.a.run.app/privacy`
5. Verify these scopes are listed:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/fitness.activity.read`
   - `https://www.googleapis.com/auth/fitness.body.read`
   - `https://www.googleapis.com/auth/fitness.sleep.read`
   - `https://www.googleapis.com/auth/calendar.events`

**Note:** Users who connected Google before the calendar scope was added will need to reconnect.

### 2. Data Persistence Setup (RECOMMENDED)
**Why:** Current SQLite database is ephemeral - data is lost when Cloud Run restarts

**Current Status:**
- ✅ Local development: SQLite works fine
- ⚠️ Production: Data is lost on container restart/redeploy

**Options:**

#### Option A: Cloud SQL (Recommended)
**Best for:** Production use, multiple users, data persistence required

**Cost:** ~$7-10/month for smallest instance (db-f1-micro)

**Setup:**
```bash
# 1. Create Cloud SQL instance
gcloud sql instances create ai-planner-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# 2. Create database
gcloud sql databases create ai_planner --instance=ai-planner-db

# 3. Create user
gcloud sql users create dbuser \
  --instance=ai-planner-db \
  --password=YOUR_SECURE_PASSWORD

# 4. Get connection name
gcloud sql instances describe ai-planner-db --format="value(connectionName)"
# Output: your-project:us-central1:ai-planner-db

# 5. Update Cloud Run service
gcloud run services update ai-activity-planner \
  --region us-central1 \
  --add-cloudsql-instances YOUR_PROJECT:us-central1:ai-planner-db \
  --set-env-vars "DATABASE_URL=postgresql://dbuser:YOUR_PASSWORD@/ai_planner?host=/cloudsql/YOUR_PROJECT:us-central1:ai-planner-db"

# 6. Run migration on Cloud SQL
# Install Cloud SQL Proxy locally, then:
./cloud_sql_proxy -instances=YOUR_PROJECT:us-central1:ai-planner-db=tcp:5432
# In another terminal:
DATABASE_URL=postgresql://dbuser:YOUR_PASSWORD@localhost:5432/ai_planner python migrate_db.py
```

**Pros:**
- Production-grade database
- Automatic backups
- High availability
- Scales independently

**Cons:**
- Additional cost
- More complex setup

#### Option B: Keep SQLite + Accept Data Loss
**Best for:** Development, demos, testing

**Cost:** $0

**Setup:** No changes needed

**Pros:**
- No additional cost
- Simple
- Works for testing

**Cons:**
- Data lost on every deployment
- Not suitable for real users
- No backups

### 3. Environment Variables Check
Verify these are set in Cloud Run:
```bash
gcloud run services describe ai-activity-planner \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

Required variables:
- `SECRET_KEY` - Your Flask secret key
- `OPENAI_API_KEY` - Your OpenAI API key
- `DATABASE_URL` - (Only if using Cloud SQL)

### 4. Run Database Migration
**If using Cloud SQL:**
```bash
# Connect to Cloud SQL and run migration
DATABASE_URL=postgresql://... python migrate_db.py
```

**If using SQLite (ephemeral):**
- Migration runs automatically on first app start via `db.create_all()`
- No action needed, but data will be lost on restart

### 5. Test the Deployment
After deploying:
- [ ] Visit `/terms` - Should load Terms of Service
- [ ] Visit `/privacy` - Should load Privacy Policy
- [ ] Login and visit `/settings` - Should load settings page
- [ ] Update profile in settings - Should save successfully
- [ ] Connect Google account - Should request calendar permission
- [ ] Export plan to Google Calendar - Should work
- [ ] Delete test account - Should work
- [ ] Check footer links appear on all pages

### 6. Notify Existing Users
If you have existing users:

**Email template:**
```
Subject: Important Updates to AI Activity Planner

Hi,

We've made some exciting updates to AI Activity Planner:

✨ New Features:
- User Settings page - Update your profile, timezone, and preferences
- Google Calendar export - Export your activity plans with one click
- Edit activities - Modify activities directly from the Log page

🔒 Legal Updates:
- Terms of Service: https://your-app-url/terms
- Privacy Policy: https://your-app-url/privacy

⚙️ Action Required:
If you previously connected Google, please reconnect to grant calendar access:
1. Go to Settings
2. Click "Disconnect" under Google
3. Click "Connect" and approve the new permissions

[Optional: Data persistence notice]
Note: We're currently migrating to a persistent database. Your data may be 
temporarily unavailable during this transition.

Thanks for using AI Activity Planner!
```

## 📋 Deployment Commands

### Deploy with current settings (SQLite, ephemeral):
```bash
gcloud run deploy ai-activity-planner \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Deploy with Cloud SQL (after setup):
```bash
gcloud run deploy ai-activity-planner \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances YOUR_PROJECT:us-central1:ai-planner-db \
  --set-env-vars "DATABASE_URL=postgresql://dbuser:password@/ai_planner?host=/cloudsql/YOUR_PROJECT:us-central1:ai-planner-db"
```

## 🧪 Local Testing

Before deploying, test locally:

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run migration (if database exists)
python migrate_db.py

# 3. Start app
python app.py

# 4. Test in browser
# Visit: http://localhost:5000
# Test: Login, Settings, Terms, Privacy, Edit, Calendar Export

# 5. Test settings page
# - Update profile fields
# - Change timezone
# - Test delete account (use test account!)

# 6. Test calendar export
# - Connect Google (will need to update OAuth redirect URIs for localhost)
# - Generate a plan
# - Click export to calendar
```

## 📝 Post-Deployment Tasks

After successful deployment:
- [ ] Update Google OAuth console with Terms/Privacy URLs
- [ ] Test all new features in production
- [ ] Monitor logs for errors: `gcloud run logs read ai-activity-planner --region us-central1`
- [ ] Set up monitoring/alerting (optional)
- [ ] Update documentation with production URLs
- [ ] Announce new features to users

## ⚠️ Known Issues / Limitations

1. **Data Persistence:** Currently using ephemeral SQLite - data lost on restart
   - **Solution:** Set up Cloud SQL (see Option A above)

2. **Calendar Scope:** Users who connected Google before need to reconnect
   - **Workaround:** Disconnect and reconnect in Settings

3. **Migration Script:** Only works with SQLite, needs adaptation for PostgreSQL
   - **Solution:** Use Cloud SQL Proxy for PostgreSQL migrations

4. **No Email Verification:** Email addresses aren't verified
   - **Future:** Add email verification flow

5. **No Password Reset:** Users can't reset forgotten passwords
   - **Future:** Add password reset via email

## 📊 Monitoring

After deployment, monitor:
```bash
# View logs
gcloud run logs read ai-activity-planner --region us-central1 --limit 50

# View service status
gcloud run services describe ai-activity-planner --region us-central1

# View metrics (Cloud Console)
# Go to: Cloud Run → ai-activity-planner → Metrics
```

## 🔄 Rollback Plan

If something goes wrong:
```bash
# List revisions
gcloud run revisions list --service=ai-activity-planner --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic ai-activity-planner \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100
```

---

**Last Updated:** December 7, 2025  
**Next Review:** Before production deployment
