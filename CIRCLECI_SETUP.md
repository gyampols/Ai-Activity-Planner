# CircleCI Deployment Setup Guide

This guide will help you set up automatic deployment to Google Cloud Run when changes are merged to the `main` branch.

## Overview

The CircleCI pipeline consists of two jobs:
1. **Test Job**: Validates Python syntax and ensures all files compile correctly
2. **Deploy Job**: Deploys the application to Google Cloud Run (only runs on `main` branch)

## Prerequisites

- CircleCI account connected to your GitHub repository
- Google Cloud Project with Cloud Run API enabled
- Service account with deployment permissions

## Step 1: Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **IAM & Admin** → **Service Accounts**
3. Click **Create Service Account**
4. Name it `circleci-deployer` and click **Create**
5. Grant the following roles:
   - **Cloud Run Admin** (roles/run.admin)
   - **Service Account User** (roles/iam.serviceAccountUser)
   - **Storage Admin** (roles/storage.admin) - for Cloud Build
6. Click **Continue** → **Done**
7. Click on the created service account
8. Go to **Keys** tab → **Add Key** → **Create New Key**
9. Choose **JSON** and click **Create**
10. Save the downloaded JSON file securely

## Step 2: Encode the Service Account Key

The service account key needs to be base64 encoded for CircleCI. **IMPORTANT**: Encode without line breaks!

```bash
# On macOS/Linux (RECOMMENDED - encodes without newlines)
cat path/to/your-service-account-key.json | base64 | tr -d '\n' | pbcopy
# This copies the encoded key to your clipboard WITHOUT newlines

# Alternative: Save to a file first
cat path/to/your-service-account-key.json | base64 | tr -d '\n' > encoded-key.txt
# Then copy the contents of encoded-key.txt

# On Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\your-service-account-key.json")) | Set-Clipboard
```

**⚠️ Critical**: Make sure there are NO newlines or spaces in your base64 string when pasting into CircleCI!

## Step 3: Set Up CircleCI Project

1. Go to [CircleCI](https://app.circleci.com/)
2. Click **Projects** in the left sidebar
3. Find your `Ai-Activity-Planner` repository
4. Click **Set Up Project**
5. Choose **Use Existing Config** (since we already have `.circleci/config.yml`)
6. Click **Set Up Project**

## Step 4: Create CircleCI Context

Contexts allow you to share environment variables across multiple projects securely.

1. In CircleCI, click **Organization Settings** (bottom left)
2. Click **Contexts** in the left menu
3. Click **Create Context**
4. Name it `gcp-deployment`
5. Click on the created context
6. Add the following environment variables:

### Required Environment Variables

Click **Add Environment Variable** for each:

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `GCLOUD_SERVICE_KEY` | *[Your base64 encoded key]* | Base64 encoded service account JSON |
| `GOOGLE_PROJECT_ID` | Your GCP Project ID | e.g., `your-project-123456` |
| `SECRET_KEY` | Your Flask secret key | Same as in Cloud Run |
| `OPENAI_API_KEY` | Your OpenAI API key | For GPT-4 planning |
| `GOOGLE_CLIENT_ID` | Your Google OAuth Client ID | For Google authentication |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth Secret | For Google authentication |
| `FITBIT_CLIENT_ID` | Your Fitbit Client ID | `23TM5J` |
| `FITBIT_CLIENT_SECRET` | Your Fitbit Client Secret | For Fitbit integration |
| `BASE_URL` | `https://ai-activity-planner-mola55j5ra-uc.a.run.app` | Your Cloud Run URL |

**Security Note**: Mark all sensitive variables as "private" in CircleCI (they are private by default).

## Step 5: Enable Cloud Build API

If not already enabled:

```bash
gcloud services enable cloudbuild.googleapis.com
```

## Step 6: Test the Pipeline

### Test on a Feature Branch

1. Create a new branch:
   ```bash
   git checkout -b test-circleci
   ```

2. Make a small change (e.g., update README.md)

3. Commit and push:
   ```bash
   git add .
   git commit -m "Test CircleCI pipeline"
   git push origin test-circleci
   ```

4. Check CircleCI dashboard - you should see the **test** job running (deploy will NOT run)

### Deploy from Main Branch

Once the test passes on your feature branch:

1. Merge to main:
   ```bash
   git checkout main
   git merge test-circleci
   git push origin main
   ```

2. Check CircleCI dashboard - you should see both **test** and **deploy** jobs running

3. After successful deployment, verify at: https://ai-activity-planner-mola55j5ra-uc.a.run.app

## Workflow Summary

```
Feature Branch Push → Test Job Runs → (Deploy Skipped)
                                        ↓
                                   Pass/Fail Reported
                                        
Main Branch Merge  → Test Job Runs → Deploy Job Runs → Cloud Run Updated
```

## Pipeline Features

✅ **Automatic Testing**: Every push runs Python syntax validation
✅ **Protected Deployment**: Only `main` branch triggers deployment
✅ **Dependency Caching**: Faster builds with pip cache
✅ **Environment Variables**: Secure injection of secrets
✅ **Zero-Downtime Deployment**: Cloud Run handles traffic switching

## Troubleshooting

### Issue: "Permission denied" during deployment

**Solution**: Ensure your service account has the required roles:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:circleci-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

### Issue: "Unable to decode GCLOUD_SERVICE_KEY" or "Expecting value: line 2 column 1"

**Problem**: The base64-encoded service account key has newlines or is corrupted.

**Solution**: Re-encode your service account key WITHOUT newlines:
```bash
# Remove the old environment variable from CircleCI first
# Then re-encode properly:
cat service-account-key.json | base64 | tr -d '\n' > encoded-key.txt
# Copy contents of encoded-key.txt (it should be ONE long line with no breaks)
cat encoded-key.txt
```

**Steps to fix in CircleCI**:
1. Go to Organization Settings → Contexts → `gcp-deployment`
2. Click on `GCLOUD_SERVICE_KEY` environment variable
3. Click **Remove Environment Variable**
4. Add it again with the newly encoded value (no newlines!)
5. Re-run the failed pipeline

### Issue: Build fails with "context not found"

**Solution**: Ensure you created the context named exactly `gcp-deployment` and added all environment variables.

### Issue: Deployment succeeds but app doesn't work

**Solution**: Check if all environment variables are set correctly in CircleCI context. Missing variables will cause runtime errors.

## Monitoring Deployments

- **CircleCI Dashboard**: https://app.circleci.com/pipelines/github/gyampols/Ai-Activity-Planner
- **Cloud Run Console**: https://console.cloud.google.com/run
- **Cloud Run Logs**: `gcloud run logs read ai-activity-planner --region=us-central1`

## Optional: Add Status Badge to README

Add this to your README.md to show build status:

```markdown
[![CircleCI](https://circleci.com/gh/gyampols/Ai-Activity-Planner/tree/main.svg?style=shield)](https://circleci.com/gh/gyampols/Ai-Activity-Planner/tree/main)
```

## Cost Considerations

- **CircleCI**: Free tier includes 6,000 build minutes/month (this pipeline uses ~2-3 minutes per build)
- **Google Cloud Build**: Free tier includes 120 build-minutes/day
- **Cloud Run**: Free tier sufficient for personal use (as previously discussed)

All within free tiers for typical personal project usage! 🎉
