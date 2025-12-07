# 📁 Code Structure

## Overview
The application has been refactored into a clean, modular architecture for better maintainability, readability, and scalability.

## Directory Structure

```
Ai-Activity-Planner/
├── app.py                      # Main application entry point
├── config.py                   # Configuration and environment variables
├── models.py                   # Database models (User, Activity, Appointment)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
│
├── routes/                     # Blueprint modules for routes
│   ├── __init__.py
│   ├── main.py                # Basic pages (home, about, utilities)
│   ├── auth.py                # Authentication (login, signup, OAuth)
│   ├── activities.py          # Activity & appointment CRUD
│   ├── planning.py            # AI-powered weekly planning
│   └── integrations.py        # Third-party integrations (Fitbit, Google, Oura)
│
├── utils/                      # Utility functions
│   ├── __init__.py
│   └── helpers.py             # Weather, geolocation, API helpers
│
├── services/                   # Service modules
│   └── __init__.py
│
├── templates/                  # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── log.html
│   └── plan.html
│
└── instance/                   # Instance-specific data
    └── activities.db          # SQLite database
```

## Module Responsibilities

### `app.py` - Application Factory
- Creates and configures the Flask application
- Initializes extensions (database, CSRF, login manager)
- Registers all blueprints
- Minimal and focused on app setup only

### `config.py` - Configuration Management
- Centralizes all environment variables
- Defines configuration class
- Provides properties for dynamic URLs (OAuth callbacks)
- Single source of truth for all settings

### `models.py` - Database Models
- User model (authentication, preferences, OAuth tokens)
- Activity model (user activities with preferences)
- Appointment model (scheduled responsibilities)

### `routes/` - Route Blueprints

#### `main.py` - Core Pages
- **Routes:**
  - `/` - Home page
  - `/about` - About page
  - `/search_cities` - City search API
  - `/toggle_temperature_unit` - Toggle C/F preference

#### `auth.py` - Authentication
- **Routes:**
  - `/login` - Username/password login
  - `/signup` - User registration
  - `/logout` - User logout
  - `/login/google` - Initiate Google OAuth
  - `/callback/google` - Handle Google OAuth callback
- **Functions:**
  - `is_safe_url()` - Prevent open redirect vulnerabilities

#### `activities.py` - Activity Management
- **Routes:**
  - `/log` - View activities and appointments
  - `/add_activity` - Create new activity
  - `/delete_activity/<id>` - Delete activity
  - `/add_appointment` - Create appointment
  - `/delete_appointment/<id>` - Delete appointment
- **Features:**
  - Input validation
  - Duration parsing
  - Preferred time/days handling

#### `planning.py` - AI Planning
- **Routes:**
  - `/plan` - Planning page
  - `/generate_plan` - Generate AI weekly plan
- **Functions:**
  - `_build_planning_prompt()` - Constructs OpenAI prompt
  - `_generate_mock_plan()` - Fallback when no API key
- **Features:**
  - Weather-aware planning
  - Biometric data integration
  - Appointment conflict avoidance
  - Sunrise/sunset consideration
  - JSON response parsing

#### `integrations.py` - Third-Party Services
- **Routes:**
  - `/connect_fitbit` - Initiate Fitbit OAuth
  - `/callback/fitbit` - Handle Fitbit callback
  - `/connect/google` - Connect Google Fit
  - `/callback/connect-google` - Handle Google connect
  - `/connect_oura` - Connect Oura ring
  - `/disconnect_*` - Disconnect services
- **Functions:**
  - `_fetch_fitbit_readiness()` - Get readiness score
  - `_fetch_fitbit_sleep()` - Get sleep metrics
- **Features:**
  - OAuth flow management
  - Token storage and refresh
  - Biometric data fetching

### `utils/helpers.py` - Utility Functions
- **Functions:**
  - `get_location_from_ip()` - IP-based geolocation
  - `search_cities(query)` - Geocoding city search
  - `get_weather_forecast(location, unit)` - 7-day forecast
- **APIs Used:**
  - ipapi.co (IP geolocation)
  - Open-Meteo (weather and geocoding)

## Design Patterns

### 1. Application Factory Pattern
The `create_app()` function allows for:
- Easy testing with different configurations
- Multiple app instances
- Clear initialization sequence

### 2. Blueprint Pattern
Each feature area is a separate blueprint:
- **Separation of Concerns:** Related routes grouped together
- **Modularity:** Features can be developed/tested independently
- **Scalability:** Easy to add new feature blueprints

### 3. Configuration Management
Single `config.py` file:
- Environment-based configuration
- No hardcoded values in code
- Easy to modify for different environments

### 4. Utility Functions
Reusable helpers in `utils/`:
- DRY (Don't Repeat Yourself)
- Easy to test
- Clear single responsibility

## Data Flow

### 1. User Authentication
```
User → /login → auth.py → User model → Session → Redirect
```

### 2. Activity Planning
```
User → /plan → planning.py → helpers.get_weather_forecast()
                           → OpenAI API
                           → JSON response
                           → Template rendering
```

### 3. Fitbit Integration
```
User → /connect_fitbit → integrations.py → Fitbit OAuth
                                         → Fitbit API
                                         → User model (update)
                                         → Redirect
```

## Environment Variables

Required in `.env` file:
```bash
# Flask
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///activities.db

# OpenAI
OPENAI_API_KEY=sk-...

# OAuth
BASE_URL=http://localhost:5000
OAUTHLIB_INSECURE_TRANSPORT=1  # Set to 0 in production

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Fitbit OAuth
FITBIT_CLIENT_ID=...
FITBIT_CLIENT_SECRET=...
```

## API Dependencies

### External APIs (Free)
- **Open-Meteo:** Weather forecasts, geocoding, sunrise/sunset
- **ipapi.co:** IP-based geolocation

### External APIs (Requires Key)
- **OpenAI GPT-4:** AI-powered activity planning
- **Google OAuth:** User authentication, Google Fit data
- **Fitbit API:** Biometric data (readiness, sleep scores)

## Testing

To test the refactored application:

```bash
# Start the app
python app.py

# The app should start without errors on http://localhost:5000
```

### Test Checklist
- ✅ Homepage loads
- ✅ Login/signup works
- ✅ Activity CRUD operations
- ✅ AI planning generates schedules
- ✅ OAuth flows (Google, Fitbit)
- ✅ Weather forecast displays
- ✅ Temperature unit toggle

## Benefits of Refactoring

### Before (1153 lines in app.py)
- ❌ Hard to navigate
- ❌ Difficult to test individual features
- ❌ Merge conflicts more likely
- ❌ Unclear dependencies

### After (Modular structure)
- ✅ Easy to find specific functionality
- ✅ Each module can be tested independently
- ✅ Team can work on different modules
- ✅ Clear separation of concerns
- ✅ Simple to add new features
- ✅ Better code organization

## Future Enhancements

The modular structure makes it easy to add:

1. **New Integrations:** Add new file in `routes/`
2. **New Utilities:** Add functions in `utils/`
3. **New APIs:** Extend `utils/helpers.py`
4. **Testing:** Create `tests/` directory mirroring structure
5. **API Routes:** Create `routes/api.py` for REST API
6. **Admin Panel:** Create `routes/admin.py`

## Migration Notes

- Original app.py backed up as `app_old.py`
- Database structure unchanged (no migration needed)
- All routes maintain same URLs (backward compatible)
- Environment variables remain the same

## Maintenance

### Adding a New Route
1. Choose appropriate blueprint (or create new)
2. Add route function
3. Import any needed utilities
4. Update templates if needed

### Adding a New Integration
1. Create new route in `routes/integrations.py`
2. Add OAuth configuration to `config.py`
3. Add callback route
4. Update User model if new fields needed

### Modifying Configuration
1. Update `config.py` only
2. All modules automatically use new config
3. No need to update multiple files

This structure ensures the codebase remains clean, maintainable, and easy to understand for both current and future developers.
