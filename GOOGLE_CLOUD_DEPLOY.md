# 🚀 Google Cloud Deployment Guide

## Quick Deploy (5 Minutes)

### Step 1: Install Google Cloud SDK

```bash
# macOS
brew install google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install
```

### Step 2: Login and Setup Project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create YOUR-PROJECT-ID --name="AI Activity Planner"

# Set as active project
gcloud config set project YOUR-PROJECT-ID

# Enable billing (required for deployment)
# Go to: https://console.cloud.google.com/billing
```

### Step 3: Deploy to Cloud Run (Recommended)

```bash
# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Deploy your app
gcloud run deploy ai-activity-planner \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi
```

**That's it!** Your app will be live at: `https://ai-activity-planner-XXXXX-uc.a.run.app`

---

## Environment Variables

After deployment, add your API keys:

```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Update Cloud Run with environment variables
gcloud run services update ai-activity-planner \
  --region=us-central1 \
  --set-env-vars="SECRET_KEY=YOUR-GENERATED-SECRET,OPENAI_API_KEY=sk-...,BASE_URL=https://your-app-url.run.app,OAUTHLIB_INSECURE_TRANSPORT=0"
```

### Optional API Keys (for full features):

```bash
# Add Google OAuth
gcloud run services update ai-activity-planner \
  --region=us-central1 \
  --update-env-vars="GOOGLE_CLIENT_ID=your-id,GOOGLE_CLIENT_SECRET=your-secret"

# Add Fitbit OAuth
gcloud run services update ai-activity-planner \
  --region=us-central1 \
  --update-env-vars="FITBIT_CLIENT_ID=your-id,FITBIT_CLIENT_SECRET=your-secret"
```

---

## Update OAuth Redirect URIs

### For Google OAuth:
1. Go to: https://console.cloud.google.com/apis/credentials
2. Click on your OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs**:
   - `https://your-app-url.run.app/callback/google`
   - `https://your-app-url.run.app/callback/connect-google`

### For Fitbit OAuth:
1. Go to: https://dev.fitbit.com/apps
2. Update **OAuth 2.0 Application Type** redirect URL:
   - `https://your-app-url.run.app/callback/fitbit`

---

## Alternative: Google App Engine

If you prefer App Engine over Cloud Run:

```bash
# Deploy to App Engine
gcloud app deploy

# View your app
gcloud app browse
```

Your app will be at: `https://YOUR-PROJECT-ID.uc.r.appspot.com`

**Note**: Update `app.yaml` with your environment variables before deploying.

---

## Database Persistence (Optional)

By default, SQLite data is stored in the container and resets on redeployment.

### For Production: Use Cloud SQL

```bash
# Create PostgreSQL instance
gcloud sql instances create activity-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create activities --instance=activity-db

# Get connection name
gcloud sql instances describe activity-db --format="value(connectionName)"

# Update Cloud Run to use Cloud SQL
gcloud run services update ai-activity-planner \
  --region=us-central1 \
  --add-cloudsql-instances=YOUR-CONNECTION-NAME \
  --set-env-vars="DATABASE_URL=postgresql://user:password@/activities?host=/cloudsql/YOUR-CONNECTION-NAME"
```

---

## Custom Domain (Optional)

```bash
# Map your domain to Cloud Run
gcloud run domain-mappings create \
  --service=ai-activity-planner \
  --domain=yourdomain.com \
  --region=us-central1

# Follow DNS setup instructions shown after command
```

---

## Monitoring & Logs

### View logs:
```bash
# Stream logs in real-time
gcloud run logs tail ai-activity-planner --region=us-central1

# View logs in browser
https://console.cloud.google.com/run/detail/us-central1/ai-activity-planner/logs
```

### Check service status:
```bash
gcloud run services describe ai-activity-planner --region=us-central1
```

---

## Cost Estimates

### Cloud Run Pricing:
- **Free Tier**: 2 million requests/month, 360,000 GB-seconds/month
- **Cost**: ~$0.40 per million requests after free tier
- **Idle cost**: $0 when not in use (min-instances=0)
- **Estimated**: $0-5/month for personal use

### Cloud SQL (if used):
- **db-f1-micro**: ~$7.67/month
- **10GB storage**: ~$1.70/month

---

## Troubleshooting

### Issue: "Permission denied" during deployment
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login
```

### Issue: OAuth redirect URI mismatch
- Ensure your `BASE_URL` environment variable matches your deployed URL exactly
- Update OAuth app settings with correct redirect URIs
- Set `OAUTHLIB_INSECURE_TRANSPORT=0` in production

### Issue: App crashes or times out
```bash
# Check logs
gcloud run logs tail ai-activity-planner --region=us-central1

# Increase memory if needed
gcloud run services update ai-activity-planner \
  --region=us-central1 \
  --memory=1Gi
```

### Issue: Database resets on redeploy
- This is expected with SQLite in containers
- Migrate to Cloud SQL for persistent storage (see Database Persistence section)

---

## Useful Commands

```bash
# List all Cloud Run services
gcloud run services list

# Get service URL
gcloud run services describe ai-activity-planner \
  --region=us-central1 \
  --format="value(status.url)"

# Delete service
gcloud run services delete ai-activity-planner --region=us-central1

# Update service with new code
gcloud run deploy ai-activity-planner --source . --region=us-central1

# View all environment variables
gcloud run services describe ai-activity-planner \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"

# Remove environment variable
gcloud run services update ai-activity-planner \
  --region=us-central1 \
  --remove-env-vars="KEY_NAME"
```

---

## Security Checklist

- [x] Generate strong `SECRET_KEY`
- [x] Use HTTPS only (automatic with Cloud Run)
- [ ] Enable Cloud Armor for DDoS protection (optional)
- [ ] Set up Cloud Secret Manager for sensitive data
- [ ] Configure Cloud IAM permissions
- [ ] Enable audit logging
- [ ] Set up VPC for Cloud SQL (if using)

---

## CI/CD with Cloud Build (Advanced)

Create `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'ai-activity-planner'
      - '--source=.'
      - '--region=us-central1'
      - '--platform=managed'
```

Connect to GitHub:
```bash
gcloud builds triggers create github \
  --repo-name=Ai-Activity-Planner \
  --repo-owner=gyampols \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## Support Resources

- **Cloud Run Docs**: https://cloud.google.com/run/docs
- **App Engine Docs**: https://cloud.google.com/appengine/docs
- **Cloud SQL Docs**: https://cloud.google.com/sql/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator
- **Support**: https://cloud.google.com/support

---

## Next Steps

1. ✅ Deploy to Cloud Run
2. ⚙️ Configure environment variables
3. 🔐 Update OAuth redirect URIs
4. 🧪 Test all functionality
5. 📊 Monitor usage and costs
6. 🗄️ (Optional) Migrate to Cloud SQL
7. 🌐 (Optional) Add custom domain
8. 🔄 (Optional) Setup CI/CD

---

**Need help?** Check the logs first:
```bash
gcloud run logs tail ai-activity-planner --region=us-central1
```
