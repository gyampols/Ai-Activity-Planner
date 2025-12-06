# AI Activity Planner 🏃‍♂️🤖

An intelligent Flask-based web application that creates personalized weekly activity plans using AI, weather data, and fitness tracker insights.

## Features

### 🔐 User Authentication
- Secure signup and login system with username/password
- **Google OAuth integration** - Sign in with Google account
- Option to connect Google account to existing username/password account
- Password hashing with Werkzeug
- Session management with Flask-Login

### 📝 Activity Management
- Log your favorite activities with detailed information:
  - Activity name and description
  - Location preferences
  - Duration (in minutes)
  - Intensity levels (Low, Medium, High)
  - Dependencies (weather, equipment, etc.)
- Edit and delete activities
- View all your logged activities

### 🌤️ Weather Integration
- **Automatic location detection** based on your IP address
- **Smart city search** with autocomplete dropdown
- Automatic 7-day weather forecast using Open-Meteo API
- Temperature and precipitation forecasts
- Weather-aware activity scheduling

### 📊 Fitness Tracker Integration
- Connect Fitbit or Oura accounts (mock implementation)
- Track readiness scores (0-100)
- AI adjusts plans based on recovery needs:
  - Low readiness (<60): Lighter activities and more rest
  - Moderate readiness (60-80): Balanced schedule
  - High readiness (>80): Higher intensity activities

### 🤖 AI-Powered Weekly Planning
- **OpenAI GPT-4** integration for intelligent scheduling
- Creates balanced weekly activity plans considering:
  - Your logged activities and preferences
  - Current weather forecast
  - Fitness tracker readiness scores
  - Activity intensity and dependencies
  - Need for rest and recovery
- Avoids outdoor activities during bad weather
- Distributes intensity throughout the week

### 📅 Visual Calendar View
- Interactive weekly calendar display
- Each day shows:
  - Scheduled activity or rest day
  - Planning rationale and notes
  - Weather conditions (temperature, precipitation)
- Color-coded for easy visualization
- Responsive design for mobile, tablet, and desktop

## Technology Stack

- **Backend**: Flask 3.0.0, Python 3.14+
- **Database**: SQLAlchemy with SQLite (upgradeable to PostgreSQL/MySQL)
- **Authentication**: Flask-Login with secure password hashing + Google OAuth 2.0
- **AI**: OpenAI GPT-4 API
- **Weather & Geolocation**: Open-Meteo API and ipapi.co (free, no keys required)
- **Frontend**: Jinja2 templates, modern CSS, vanilla JavaScript
- **Deployment**: Google App Engine ready

## Quick Start

### Prerequisites
- Python 3.9 or higher
- pip package manager
- (Optional) OpenAI API key for AI-powered planning

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/gyampols/Ai-Activity-Planner.git
cd Ai-Activity-Planner
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env and add your configuration:
# - SECRET_KEY: Generate a random secret key
# - OPENAI_API_KEY: Your OpenAI API key (optional, will use mock data without it)
# - GOOGLE_CLIENT_ID: Google OAuth client ID (optional, for Google sign-in)
# - GOOGLE_CLIENT_SECRET: Google OAuth client secret (optional)
```

**Setting up Google OAuth (optional):**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Set authorized redirect URIs:
   - `http://localhost:5000/callback/google`
   - `http://localhost:5000/callback/connect-google`
6. Copy Client ID and Client Secret to your `.env` file

5. **Run the application**
```bash
python app.py
```

6. **Access the app**
Open your browser and navigate to `http://localhost:5000`

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to:
- Google App Engine
- Other cloud platforms
- Production best practices

## Usage Guide

1. **Sign Up**: Create an account with username/email/password OR sign in with Google
2. **Log Activities**: Add activities you enjoy with all relevant details
3. **Set Location**: Your location is auto-detected, or search for a different city
4. **Connect Accounts**: (Optional) Connect Google account for fitness data access
5. **Connect Tracker**: (Optional) Connect Fitbit or Oura for readiness data
6. **Generate Plan**: Click the AI planning button to create your weekly schedule
7. **View Calendar**: See your personalized week on the interactive calendar

## Project Structure

```
Ai-Activity-Planner/
├── app.py                 # Main Flask application
├── models.py             # Database models (User, Activity)
├── requirements.txt      # Python dependencies
├── app.yaml             # Google App Engine configuration
├── .env.example         # Environment variables template
├── DEPLOYMENT.md        # Deployment guide
├── templates/           # HTML templates
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Home page
│   ├── about.html      # About page
│   ├── login.html      # Login page
│   ├── signup.html     # Signup page
│   ├── log.html        # Activity logging page
│   └── plan.html       # Planning and calendar page
└── static/             # Static files (CSS, JS, images)
```

## API Keys

- **OpenAI API**: Optional - get from https://platform.openai.com/
  - Without key: Uses mock planning responses
  - With key: Full GPT-4 powered planning
- **Google OAuth**: Optional - get from https://console.cloud.google.com/
  - Without: Users can only sign up with username/password
  - With: Users can sign in with Google and access fitness data
- **Weather & Geolocation APIs**: No keys required - uses free services
- **Fitness Trackers**: Currently mock implementation (will use Google Fit API when connected)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- OpenAI for GPT API
- Open-Meteo for free weather data
- Flask and SQLAlchemy communities
