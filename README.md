# AI Activity Planner

A production-grade Flask application for AI-powered weekly activity planning with weather integration, fitness tracking, and calendar sync.

**Live App:** https://ai-activity-planner-300000255718.us-central1.run.app

## Features

- **AI-Powered Planning**: GPT-4 generates personalized weekly schedules
- **Weather Integration**: 7-day forecasts with sunrise/sunset times
- **Fitness Tracking**: Fitbit, Oura, and manual score input
- **Google Calendar Sync**: One-click export with duplicate detection
- **Subscription Tiers**: Free (3 plans/week) and Paid (unlimited) via Stripe
- **User Authentication**: Email/password and Google OAuth
- **Persistent Sessions**: 30-day remember-me cookies
- **Responsive Design**: Mobile-optimized UI

## Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy, PostgreSQL
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **APIs**: OpenAI GPT-4, Open-Meteo Weather, Google Calendar, Stripe
- **Infrastructure**: Google Cloud Run, Cloud SQL
- **Authentication**: Flask-Login, Google OAuth 2.0
- **Email**: SendGrid

## Project Structure

```
├── app.py              # Application factory
├── config.py           # Configuration settings
├── models.py           # SQLAlchemy ORM models
├── requirements.txt    # Python dependencies
├── routes/             # Blueprint route handlers
│   ├── activities.py   # Activity/appointment CRUD
│   ├── admin.py        # Admin panel
│   ├── auth.py         # Authentication & OAuth
│   ├── integrations.py # Fitbit, Google, Oura
│   ├── main.py         # Core routes
│   ├── payment.py      # Stripe payments
│   └── planning.py     # AI planning & calendar
├── utils/              # Utility modules
│   ├── email.py        # SendGrid email
│   ├── helpers.py      # Weather & geolocation
│   └── status_logger.py # Audit logging
├── templates/          # Jinja2 templates
├── static/             # CSS, JS, images
└── scripts/            # Migration scripts (archived)
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
STRIPE_SECRET_KEY=your-stripe-secret
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable
STRIPE_WEBHOOK_SECRET=your-stripe-webhook
SENDGRID_API_KEY=your-sendgrid-key
```

### Local Development
```bash
pip install -r requirements.txt
python app.py
```

### Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for Google Cloud Run deployment.

## Architecture

The application follows a modular Flask architecture:

- **Application Factory** (`app.py`): Creates and configures the Flask app
- **Blueprints** (`routes/`): Organized route handlers by feature
- **ORM Models** (`models.py`): SQLAlchemy models with relationships
- **Utilities** (`utils/`): Reusable helper functions
- **Configuration** (`config.py`): Environment-based settings

Database migrations are applied automatically on startup via SQLAlchemy.

## How to Use the App

### 1. Sign Up and Login

Visit the app and create an account or log in with your Google account.

**Features:**
- Email/password authentication
- Google OAuth single sign-on
- Secure session management

### 2. Configure Your Profile

Navigate to **Settings** to set up your profile:

**What to configure:**
- **Location**: Your city/zip code for weather data
- **Temperature Unit**: Celsius or Fahrenheit
- **Personal Info**: Age, gender, height, weight (optional, for better AI recommendations)

### 3. Add Your Activities

Go to the **Log** page to add activities you enjoy:

**Activity Details:**
- **Name**: e.g., "Morning Run", "Yoga", "Swimming"
- **Location**: Where you do this activity
- **Duration**: How long it typically takes
- **Intensity**: Low, Medium, High, or Very High
- **Dependencies**: Requirements like "Good weather" or "Gym membership"
- **Preferred Time**: Morning, Afternoon, Evening, or Night
- **Preferred Days**: Select which days of the week work best
![sample activity](static/Images/sampleActivity.png)

### 4. Add Appointments (Optional)

If you have fixed commitments, add them in the **Log** page:

**Appointment Details:**
- **Title**: e.g., "Team Meeting", "Doctor Appointment"
- **Type**: Work, School, Medical, Personal, Social, or Other
- **Date & Time**: When it occurs
- **Duration**: How long it lasts
- **Repeating**: Can repeat on specific days of the week
![alt text](static/Images/sampleAppointment.png)
**Why add appointments?**
The AI will schedule your activities around these fixed commitments, ensuring no conflicts.

### 5. Connect Fitness Trackers (Optional)

In the **Log** page, connect your fitness devices:

**Supported Integrations:**
- **Fitbit**: Syncs sleep score and readiness score
- **Oura**: Syncs sleep and readiness data
- **Manual Input**: No tracker? Enter your scores manually!

**Manual Fitness Scores:**
If you don't have a fitness tracker, scroll down on the Log page to find the "Manual Fitness Scores" section:
- **Sleep Score (0-100)**: How well you slept last night
  - 90-100: Excellent sleep
  - 70-89: Good sleep
  - 50-69: Fair sleep
  - Below 50: Poor sleep
- **Readiness Score (0-100)**: How ready you feel for activity today (based on Fitbit standards)
  - 65-100 (High): Body is well-rested and recovered
  - 30-64 (Moderate): Heart rate and recent sleep are about usual, body is balancing stress with recovery
  - 1-29 (Low): Prioritize recovery with lower intensity exercises like stretching and yoga
![fitbit](static/Images/manualScores.png)
Use the sliders to adjust your scores and click "Save Manual Scores". Update these daily for best results!

### 6. Connect Google Calendar (Optional)

Connect your Google account to enable calendar export:

**Benefits:**
- One-click export of your weekly plan
- Events created with proper times and durations
- Automatic conflict prevention

### 7. Generate Your Weekly Plan

Navigate to the **Plan** page:

**How it works:**
1. The AI analyzes:
   - Your activities and preferences
   - 7-day weather forecast for your location
   - Your fitness/readiness scores (if available)
   - Your fixed appointments
   - Time of day and current date

2. **Optional**: Add extra instructions
   - Example: "Focus on cardio this week"
   - Example: "I'm recovering from injury, keep intensity low"
   - Example: "Plan extra rest days"
![alt text](static/Images/plan.png)
3. Click **"Generate Plan"**

4. Review your personalized weekly schedule with:
   - Specific activities for each day
   - Suggested times based on weather and preferences
   - Weather conditions for each day
   - Intensity adjustments based on your readiness

### 8. Export to Google Calendar

Once you have a plan you like:

1. Click **"Export to Google Calendar"**
2. Events will be created with:
   - Activity name and details
   - Correct start time and duration
   - Weather information in description
3. View in your Google Calendar app or web interface

### 9. Update and Iterate

As your week progresses:
- Update your fitness scores daily (if using manual input)
- Add new activities as you discover interests
- Mark completed activities in the Log
- Generate new plans as needed
- Adjust preferences based on what works for you

## Tips for Best Results

1. **Be Specific with Activities**: Instead of "Exercise", use "30-min HIIT workout" or "Evening yoga session"

2. **Set Realistic Durations**: Include warmup/cooldown and travel time

3. **Use Dependencies**: Mark outdoor activities as weather-dependent so the AI schedules them on nice days

4. **Update Fitness Scores Regularly**: Daily updates give the AI better data for intensity recommendations

5. **Review and Adjust**: The first few plans help the AI learn your preferences - provide feedback via extra instructions

6. **Combine Fixed and Flexible**: Add appointments for must-do items, activities for flexible fitness goals

## Troubleshooting

**Weather not showing?**
- Verify your location is set correctly in Settings
- Try both city name and ZIP code formats

**Calendar export not working?**
- Ensure you've connected your Google account
- Check that you've granted calendar permissions

**Fitness scores not updating?**
- Manual scores: Use the sliders on the Log page, not the Plan page
- Fitbit/Oura: Disconnect and reconnect if data seems stale

**Plan seems off?**
- Add more detail in "Extra Instructions"
- Verify your activity preferences (time/day/intensity)
- Check that your fitness scores reflect your current state

## License

