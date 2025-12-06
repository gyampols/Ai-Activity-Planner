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

- For production, use Cloud SQL instead of SQLite for the database
- Store secrets in Google Secret Manager instead of environment variables
- Enable HTTPS (automatically provided by App Engine)
- Consider setting up Cloud Build for CI/CD

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
