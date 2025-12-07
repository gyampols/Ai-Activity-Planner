# FREE Data Persistence Setup Guide

## Overview
This guide sets up **FREE** persistent data storage for your AI Activity Planner using Cloud SQL's free tier.

## Why This is FREE ✅

- **Cloud SQL Free Tier:** db-f1-micro instances are free within certain limits
- **No ongoing costs** for small personal projects
- **Persistent storage:** User data survives deployments and restarts

## What's Being Set Up

1. **Cloud SQL PostgreSQL Instance** (free tier)
   - Database: `ai_planner`
   - User: `appuser`
   - Instance: `ai-planner-db`

2. **Cloud Run Connection**
   - Connects your app to the database
   - Uses Unix socket connection (more secure)

3. **Database Migration**
   - Transfers schema to PostgreSQL
   - All user data will persist

## Current Setup Status

### Step 1: Create Cloud SQL Instance ✅ (In Progress)
```bash
gcloud sql instances create ai-planner-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --no-backup \
  --storage-type=HDD \
  --storage-size=10GB
```
**Status:** Creating (3-5 minutes)

### Step 2: Create Database (Run After Instance is Ready)
```bash
gcloud sql databases create ai_planner --instance=ai-planner-db
```

### Step 3: Create Database User
```bash
gcloud sql users create appuser \
  --instance=ai-planner-db \
  --password=YOUR_SECURE_PASSWORD
```

### Step 4: Get Connection Name
```bash
gcloud sql instances describe ai-planner-db --format="value(connectionName)"
```
This will output something like: `ai-activity-planner-cloud:us-central1:ai-planner-db`

### Step 5: Update Cloud Run with Database Connection
```bash
# Replace with your actual connection name and password
gcloud run services update ai-activity-planner \
  --region us-central1 \
  --add-cloudsql-instances ai-activity-planner-cloud:us-central1:ai-planner-db \
  --set-env-vars "DATABASE_URL=postgresql://appuser:YOUR_PASSWORD@/ai_planner?host=/cloudsql/ai-activity-planner-cloud:us-central1:ai-planner-db"
```

### Step 6: Update requirements.txt
Add PostgreSQL driver:
```bash
echo "psycopg2-binary==2.9.9" >> requirements.txt
```

### Step 7: Migrate Database Schema
Once Cloud Run is connected, the schema will be created automatically on first run via `db.create_all()` in app.py

## Cost Breakdown

### What's FREE:
- ✅ Cloud SQL db-f1-micro instance (free tier)
- ✅ 10GB storage (within free tier)
- ✅ Cloud Run (within free tier: 2M requests/month)
- ✅ Google OAuth (always free)
- ✅ Fitbit API (free for personal use)

### What You Pay For:
- 💰 OpenAI API (~$0.01-0.10 per plan generation) - **Already paying this**

**Total Additional Cost: $0/month** ✅

## Alternative: Even Simpler FREE Option

If you want something even simpler, you can use **Railway** or **Render** which include PostgreSQL for free:

### Railway (Recommended Alternative)
- **Free tier:** 500 hours/month, PostgreSQL included
- **Setup:** 5 minutes
- **URL:** https://railway.app
- **Cost:** $0/month (within free tier)

### Render
- **Free tier:** 90 days free PostgreSQL
- **After:** $7/month for persistent PostgreSQL
- **URL:** https://render.com

## Which Should You Choose?

### Cloud SQL (Current Approach)
- ✅ Stays on Google Cloud
- ✅ Free tier available
- ✅ Professional grade
- ⚠️ More complex setup

### Railway
- ✅ Easiest setup (5 minutes)
- ✅ PostgreSQL included free
- ✅ No configuration needed
- ⚠️ Need to migrate from Google Cloud

### Keep SQLite
- ✅ No setup required
- ✅ Completely free
- ❌ Data is lost on restart (current problem)

## Recommendation

**For Free + Easy:** Use Cloud SQL free tier (what we're setting up now)
- Professional solution
- Stays on Google Cloud  
- No ongoing costs
- You keep your existing deployment

**After Cloud SQL instance finishes creating (3-5 minutes), run the remaining steps above.**

---

**Current Status:** Creating Cloud SQL instance...
Check status: `gcloud sql instances describe ai-planner-db`
