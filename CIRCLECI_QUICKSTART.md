# CircleCI CI/CD Pipeline - Quick Reference

## What Was Set Up

✅ **CircleCI Configuration** (`.circleci/config.yml`)
- Automated testing on every push
- Automatic deployment to Google Cloud Run on `main` branch merges
- Environment variable injection for secure credentials
- Dependency caching for faster builds

✅ **Documentation**
- `CIRCLECI_SETUP.md` - Complete step-by-step setup guide
- Updated `README.md` with CI/CD information
- Updated project structure documentation

## Next Steps to Enable Auto-Deployment

### 1. Create Google Cloud Service Account

```bash
# In Google Cloud Console:
# IAM & Admin → Service Accounts → Create Service Account
# Name: circleci-deployer
# Roles: Cloud Run Admin, Service Account User, Storage Admin
# Create JSON key and download
```

### 2. Encode the Service Account Key

```bash
cat path/to/service-account-key.json | base64 | pbcopy
# This copies the base64-encoded key to your clipboard
```

### 3. Set Up CircleCI

1. Go to https://app.circleci.com/
2. Connect your GitHub repository
3. Set up the project with existing config
4. Create a context named `gcp-deployment`
5. Add these environment variables to the context:

| Variable | Value |
|----------|-------|
| `GCLOUD_SERVICE_KEY` | Base64 encoded service account JSON |
| `GOOGLE_PROJECT_ID` | Your GCP project ID |
| `SECRET_KEY` | Your Flask secret key |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Secret |
| `FITBIT_CLIENT_ID` | `23TM5J` |
| `FITBIT_CLIENT_SECRET` | Your Fitbit secret |
| `BASE_URL` | `https://ai-activity-planner-mola55j5ra-uc.a.run.app` |

### 4. Commit and Push the Changes

```bash
# Add all the new files
git add .circleci/ CIRCLECI_SETUP.md CODE_STRUCTURE.md
git add config.py routes/ utils/ services/
git add app.py app_old.py templates/ README.md

# Commit the changes
git commit -m "Add modular architecture and CircleCI auto-deployment"

# Push to your feature branch first
git push origin copilot/create-flask-website
```

### 5. Test the Pipeline

Once pushed, CircleCI will:
1. ✅ Run the **test** job (validates Python syntax)
2. ⏭️ Skip the **deploy** job (only runs on `main` branch)

### 6. Merge to Main for Auto-Deploy

```bash
# Create a Pull Request on GitHub
# Review and approve
# Merge to main

# Or merge locally:
git checkout main
git merge copilot/create-flask-website
git push origin main
```

After merging to `main`, CircleCI will:
1. ✅ Run the **test** job
2. ✅ Run the **deploy** job → Your app auto-updates at https://ai-activity-planner-mola55j5ra-uc.a.run.app

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Developer makes changes in feature branch                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Push to GitHub → CircleCI runs TEST job                    │
│  ✓ Validates Python syntax                                  │
│  ✓ Ensures all modules compile                              │
│  ✗ DOES NOT deploy (not main branch)                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ (after review)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Merge PR to main branch                                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  CircleCI runs TEST + DEPLOY jobs                           │
│  ✓ Tests pass                                               │
│  ✓ Authenticates with Google Cloud                          │
│  ✓ Deploys to Cloud Run                                     │
│  ✓ Injects environment variables                            │
│  ✓ Zero-downtime deployment                                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  Website automatically updates! 🎉                          │
│  https://ai-activity-planner-mola55j5ra-uc.a.run.app       │
└─────────────────────────────────────────────────────────────┘
```

## Pipeline Configuration Summary

**Test Job** (runs on all branches):
- Installs Python dependencies
- Validates syntax of all Python files
- Caches dependencies for faster builds

**Deploy Job** (runs only on `main` branch):
- Requires test job to pass first
- Authenticates with Google Cloud
- Deploys to Cloud Run with all environment variables
- Uses the same deployment command you used manually

## Monitoring

- **CircleCI Dashboard**: https://app.circleci.com/
- **Cloud Run Console**: https://console.cloud.google.com/run
- **Deployment Logs**: Available in CircleCI job output

## Cost Breakdown

| Service | Free Tier | Your Usage | Cost |
|---------|-----------|------------|------|
| CircleCI | 6,000 min/month | ~2-3 min/deployment | **$0** |
| Cloud Build | 120 min/day | ~1 min/deployment | **$0** |
| Cloud Run | As discussed | Personal use | **$0** |

**Total: $0/month** 🎉

## Troubleshooting

If deployment fails, check:
1. ✓ Service account has correct roles
2. ✓ All environment variables are set in CircleCI context
3. ✓ Context name is exactly `gcp-deployment`
4. ✓ GCLOUD_SERVICE_KEY is base64 encoded without line breaks

See `CIRCLECI_SETUP.md` for detailed troubleshooting steps.

## What Happens on Each Push

### Feature Branch Push
```bash
git push origin feature-branch
```
→ CircleCI runs TEST job only
→ No deployment
→ Fast feedback on code quality

### Main Branch Merge
```bash
git push origin main
```
→ CircleCI runs TEST job
→ If tests pass, runs DEPLOY job
→ App automatically updates in ~2-3 minutes
→ Zero downtime for users

## Ready to Go! 🚀

Once you complete the setup steps above, every merge to `main` will automatically deploy your changes to production. No manual deployment commands needed!
