# CircleCI CI/CD Configuration

This directory contains the CircleCI configuration for automated testing and deployment of the AI Activity Planner application.

## Setup Instructions

### 1. Connect CircleCI to Your Repository

1. Go to [CircleCI](https://circleci.com/) and sign in with your GitHub account
2. Click "Projects" in the left sidebar
3. Find your `Ai-Activity-Planner` repository and click "Set Up Project"
4. CircleCI will automatically detect the `.circleci/config.yml` file

### 2. Configure Environment Variables

In CircleCI project settings, add the following environment variables:

#### Required Environment Variables:
- `DATABASE_URL` - PostgreSQL connection string for Cloud SQL
- `SENDGRID_API_KEY` - SendGrid API key for email functionality
- `EMAIL_FROM` - Email address for sending emails
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `OPENAI_API_KEY` - OpenAI API key for AI features
- `FITBIT_CLIENT_ID` - Fitbit integration client ID
- `FITBIT_CLIENT_SECRET` - Fitbit integration client secret
- `BASE_URL` - Base URL of your application (e.g., https://ai-activity-planner-300000255718.us-central1.run.app)

### 3. Configure GCP Service Account

For deployment to Google Cloud Run, you need to set up authentication:

1. In Google Cloud Console, create a service account with the following roles:
   - Cloud Run Admin
   - Service Account User
   - Cloud SQL Client

2. Download the service account JSON key

3. In CircleCI, go to Project Settings > Contexts
4. Create a new context called `gcp-deployment`
5. Add the following environment variables to the context:
   - `GCLOUD_SERVICE_KEY` - Paste the entire contents of the service account JSON key
   - `GOOGLE_PROJECT_ID` - Your GCP project ID (ai-activity-planner-cloud)
   - `GOOGLE_COMPUTE_ZONE` - Your compute zone (us-central1)

## Workflow Overview

The CI/CD pipeline consists of three main jobs:

### 1. Test Job
- Runs on every push to any branch
- Installs Python dependencies
- Runs tests (placeholder for now - add your tests)
- Caches dependencies for faster builds

### 2. Build Job
- Runs after tests pass
- Builds Docker image
- Tags image with commit SHA and 'latest'
- Persists image for deployment

### 3. Deploy Job
- Runs only on `main` and `production` branches
- Requires build job to complete successfully
- Deploys to Google Cloud Run
- Sets all environment variables
- Connects to Cloud SQL instance

## Branch Strategy

- **All branches**: Test and build jobs run
- **main branch**: Deploys to production Cloud Run service
- **production branch**: Also deploys to production (if you use this branch)
- **Other branches**: Build and test only, no deployment

## Adding Tests

To add tests to your pipeline, update the test job in `config.yml`:

```yaml
- run:
    name: Run tests
    command: |
      . venv/bin/activate
      pytest tests/ -v --cov=.
```

Make sure to add `pytest` and `pytest-cov` to your `requirements.txt` file.

## Monitoring Deployments

1. Go to CircleCI dashboard
2. Click on your project
3. View running or completed workflows
4. Click on individual jobs to see detailed logs
5. Check Cloud Run logs for runtime issues

## Troubleshooting

### Deployment Fails
- Check that all environment variables are set correctly
- Verify GCP service account has proper permissions
- Check Cloud Run logs in GCP Console

### Build Fails
- Check for syntax errors in Python code
- Verify all dependencies are in requirements.txt
- Check Docker build logs

### Tests Fail
- Run tests locally first: `pytest tests/`
- Check for missing test dependencies
- Verify test database configuration

## Manual Deployment

If you need to deploy manually, you can still use gcloud CLI:

```bash
gcloud run deploy ai-activity-planner \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "..." \
  --add-cloudsql-instances ai-activity-planner-cloud:us-central1:ai-planner-db \
  --project ai-activity-planner-cloud
```

## Security Notes

- Never commit sensitive keys or credentials
- All secrets should be stored in CircleCI environment variables or contexts
- Service account keys should have minimal required permissions
- Regularly rotate API keys and credentials
