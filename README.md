# AI Activity Planner

A professional-grade Flask web application that generates personalized weekly activity plans using AI, real-time weather data, and fitness metrics.

**Live App:** https://ai-activity-planner-300000255718.us-central1.run.app

## Features

- **AI-Powered Planning**: GPT-4 integration for intelligent weekly activity scheduling
- **Weather Integration**: Real-time 7-day forecasts with sunrise/sunset times
- **Fitness Tracking**: Fitbit and Oura integration with manual score input option
- **Google Calendar Export**: One-click export of your weekly plan
- **User Authentication**: Secure login with Google OAuth support
- **Responsive Design**: Optimized for desktop and mobile devices

## Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy, PostgreSQL
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **APIs**: OpenAI GPT-4, Open-Meteo Weather, Google Calendar
- **Infrastructure**: Google Cloud Run, Cloud SQL
- **Authentication**: Flask-Login, Google OAuth 2.0

## Project Structure

```
├── app.py              # Application entry point
├── config.py           # Configuration management
├── models.py           # Database models
├── requirements.txt    # Python dependencies
├── routes/            # Route handlers
│   ├── activities.py  # Activity CRUD operations
│   ├── auth.py        # Authentication & OAuth
│   ├── integrations.py # Third-party integrations
│   ├── main.py        # Core app routes
│   └── planning.py    # AI planning & calendar export
├── templates/         # Jinja2 templates
├── utils/            # Helper functions
│   └── helpers.py    # Weather & geolocation utilities
└── instance/         # Runtime data (local only)
```

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL (Cloud SQL for production)
- Google Cloud account (for deployment)

### Environment Variables
Create a `.env` file:
```bash
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
DATABASE_URL=postgresql://user:pass@host/db
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python migrate_db.py

# Start development server
python app.py
```

### Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for Cloud Run deployment instructions.

## License

