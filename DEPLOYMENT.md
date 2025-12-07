# Deployment Guide

## Local Development

### Prerequisites
- Python 3.9 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gyampols/Ai-Activity-Planner.git
   cd Ai-Activity-Planner
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your configuration:
   ```
   SECRET_KEY=your-random-secret-key
   OPENAI_API_KEY=your-openai-api-key  # Optional but recommended
   DATABASE_URL=sqlite:///activities.db
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```
   
   The application will be available at `http://localhost:5000`

## Google App Engine Deployment

### Prerequisites
- Google Cloud SDK installed
- A Google Cloud project created
- Billing enabled for your Google Cloud project

### Deployment Steps

1. **Initialize gcloud:**
   ```bash
   gcloud init
   ```

2. **Set your project:**
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Update app.yaml:**
   Edit `app.yaml` and set your environment variables:
   ```yaml
   env_variables:
     SECRET_KEY: 'your-production-secret-key'
     OPENAI_API_KEY: 'your-openai-api-key'
   ```

4. **Deploy to App Engine:**
   ```bash
   gcloud app deploy
   ```

5. **View your application:**
   ```bash
   gcloud app browse
   ```

### Important Notes

- For production, use Cloud SQL instead of SQLite for the database (see Data Persistence section below)
- Store secrets in Google Secret Manager instead of environment variables
- Enable HTTPS (automatically provided by App Engine/Cloud Run)
- Consider setting up Cloud Build for CI/CD

## Cloud Run Deployment (Current Method)

### Prerequisites
- Google Cloud SDK installed
- A Google Cloud project created
- Billing enabled for your Google Cloud project
- Container Registry API enabled

### Manual Deployment Steps

1. **Build and deploy:**
   ```bash
   gcloud run deploy ai-activity-planner \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars "SECRET_KEY=your-secret-key,OPENAI_API_KEY=your-openai-key"
   ```

2. **Configure OAuth:**
   - Add the Cloud Run URL to Google OAuth console authorized redirect URIs
   - Format: `https://your-app-url/auth/google/callback`

3. **View your application:**
   The deployment will output your application URL

### Important Cloud Run Notes

- **Data Persistence:** By default, Cloud Run uses ephemeral storage (data is lost on restart)
- See the "Data Persistence Options" section below for production solutions
- Environment variables can be updated without redeployment using the Cloud Console
- Cloud Run automatically scales to zero when not in use (cost-efficient)

## Data Persistence Options

**Problem:** SQLite databases in Cloud Run are stored in ephemeral file systems. Data is lost when:
- The container restarts
- The service scales down to zero
- You deploy a new version

### Option 1: Cloud SQL (Recommended for Production)

**Pros:**
- Production-grade relational database
- Automatic backups and point-in-time recovery
- High availability options
- Scales independently from your app
- Supports PostgreSQL and MySQL

**Cons:**
- Additional cost (starts ~$7/month for smallest instance)
- Requires more setup

**Setup:**
1. Create a Cloud SQL instance:
   ```bash
   gcloud sql instances create ai-planner-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

2. Create a database:
   ```bash
   gcloud sql databases create ai_planner --instance=ai-planner-db
   ```

3. Create a user:
   ```bash
   gcloud sql users create dbuser \
     --instance=ai-planner-db \
     --password=your-secure-password
   ```

4. Update your Cloud Run service:
   ```bash
   gcloud run services update ai-activity-planner \
     --add-cloudsql-instances your-project:us-central1:ai-planner-db \
     --set-env-vars "DATABASE_URL=postgresql://dbuser:password@/ai_planner?host=/cloudsql/your-project:us-central1:ai-planner-db"
   ```

5. Update `config.py` to use the new DATABASE_URL environment variable

**Migration:** Run the migration script on Cloud SQL using Cloud SQL Proxy

### Option 2: Persistent Disk (Simpler, Limited)

**Pros:**
- Simple to set up
- Lower cost than Cloud SQL
- Works with existing SQLite code

**Cons:**
- Single instance only (no horizontal scaling)
- Manual backups required
- Not as robust as Cloud SQL

**Setup:**
1. Create a persistent disk volume
2. Mount it to `/data` in your Cloud Run service
3. Update database path to use mounted volume

**Note:** This option is not officially supported by Cloud Run for production use

### Option 3: Firestore (NoSQL Alternative)

**Pros:**
- Serverless (no infrastructure management)
- Automatic scaling
- Built-in offline support
- Free tier available

**Cons:**
- Requires code changes (different query patterns)
- NoSQL model (no relational joins)
- Different pricing model

**Implementation:** Would require rewriting database models to use Firestore SDK

### Recommendation

**For your current use case:**
- **Development/Testing:** Keep using SQLite (ephemeral is fine)
- **Production:** Use Cloud SQL PostgreSQL for data persistence

**Migration Path:**
1. Develop and test locally with SQLite
2. When ready for production with persistent data:
   - Set up Cloud SQL as shown above
   - Run database migration: `python migrate_db.py` (adapt for PostgreSQL)
   - Update environment variables
   - Redeploy

## Database Migration

After adding new database fields, run the migration script:

```bash
# Local development
python migrate_db.py

# Production (Cloud SQL)
# 1. Connect using Cloud SQL Proxy
gcloud sql connect ai-planner-db --user=dbuser

# 2. Or use the migration script with Cloud SQL connection string
DATABASE_URL=postgresql://... python migrate_db.py
```

## OpenAI API Setup

1. Go to https://platform.openai.com/
2. Create an account or sign in
3. Navigate to API keys section
4. Create a new API key
5. Add the key to your `.env` file or `app.yaml`

**Note:** The application will work without an OpenAI API key, but will provide mock responses for the planning feature.

## Fitbit/Oura Integration

Currently, the Fitbit and Oura connections are mock implementations. To implement real integration:

1. Register your app with Fitbit/Oura developer portals
2. Obtain OAuth credentials
3. Implement OAuth flow in the application
4. Use their APIs to fetch user activity data

## Database

The application uses SQLAlchemy ORM with SQLite for local development. The database includes two models:

- **User:** Stores user account information
- **Activity:** Stores user activities with details

For production on Google App Engine, consider migrating to Cloud SQL (PostgreSQL or MySQL).

## Security Considerations

### Required for Production

- **Change SECRET_KEY**: Generate a strong random secret key (not 'dev-secret-key')
- **Disable Debug Mode**: Set `debug=False` in app.run() or use gunicorn
- **Use Strong Passwords**: Enforce password complexity requirements
- **Enable HTTPS**: Automatic on App Engine, required for production
- **Secure API Keys**: Use Google Secret Manager or environment variables
- **Rate Limiting**: Implement rate limiting for API endpoints
- **CSRF Protection**: Already enabled with Flask-WTF
- **Input Validation**: All forms have validation enabled
- **XSS Protection**: All user input is properly escaped
- **SQL Injection**: SQLAlchemy ORM prevents SQL injection

### Security Features Included

✅ CSRF Protection (Flask-WTF)
✅ Password Hashing (Werkzeug)
✅ Session Management (Flask-Login)
✅ Input Validation (all forms)
✅ XSS Prevention (textContent usage)
✅ Open Redirect Protection
✅ URL Encoding (weather API)

### Production Security Checklist

- [ ] Set strong SECRET_KEY in environment
- [ ] Disable debug mode (debug=False)
- [ ] Use HTTPS only (no HTTP)
- [ ] Configure Content Security Policy headers
- [ ] Enable rate limiting
- [ ] Set up monitoring and alerts
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Use environment-specific configurations
- [ ] Enable logging for security events
