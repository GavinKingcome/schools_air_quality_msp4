# AirAware London - Air Quality Dashboard for Schools

**A Django-based real-time air quality monitoring platform for primary schools and nurseries in Lambeth and Southwark.**

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Django](https://img.shields.io/badge/django-6.0-green.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-17-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Demo Credentials](#demo-credentials)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Data Management](#data-management)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Security Notes](#security-notes)
- [Future Enhancements](#future-enhancements)
- [License](#license)

---

## 🎯 Overview

AirAware London helps parents, school administrators, and policymakers make informed decisions about children's exposure to air pollution. The platform combines real-time sensor data from the London Air Quality Network (LAQN) and Breathe London with modelled pollution data (LAEI 2022) to provide comprehensive air quality information for 133 schools across Lambeth and Southwark.

**Live Demo:** [http://127.0.0.1:8000/map/](http://127.0.0.1:8000/map/)

### Key Objectives

- **Real-time monitoring:** Hourly updates from 42 active sensors (16 LAQN + 26 Breathe London)
- **Hybrid data approach:** Direct sensor readings where available, modelled data with real-time adjustments elsewhere
- **Accessibility:** Subscription-based access (£2.50/month) with demo mode for evaluation
- **Transparency:** Clear data source attribution for every school

---

## ✨ Features

### ✅ Implemented (MVP)

- **Interactive Map Dashboard**
  - Leaflet.js map with color-coded school markers based on PM2.5 levels
  - Click markers for detailed air quality popup (NO₂, PM2.5, PM10)
  - Mobile-responsive design
  - 133 schools displayed across Lambeth and Southwark

- **Real-Time Data Integration**
  - Automated hourly data fetching via cron jobs
  - LAQN API integration (reference-grade monitoring stations)
  - Breathe London API via OpenAQ (calibrated low-cost sensors)
  - TimescaleDB optimization for time-series queries

- **Hybrid Data Strategy**
  - **Direct readings:** Schools within 150m of urban background sensors
  - **Adjusted LAEI:** LAEI 2022 baseline × real-time adjustment factor for other schools
  - Data source clearly indicated for each school

- **Subscription System**
  - Stripe integration (£2.50/month)
  - User authentication with Django's built-in auth
  - Subscription management page
  - **Demo mode enabled** for assessment (subscription requirement temporarily disabled)

- **Admin Interfaces**
  - School management (add, edit, view 133 schools)
  - Sensor management (42 sensors with filtering)
  - Readings and annual statistics views
  - User and subscription management

- **Test Coverage**
  - 39 comprehensive tests covering models, views, and data processing
  - TDD approach demonstrated

### 🔮 Planned (Future Enhancements)

- Filter schools by air quality levels
- Air quality alert notifications
- School comparison tool
- Historical trends visualization
- PDF report exports
- Full WCAG 2.1 AA accessibility compliance
- Data quality metrics dashboard

---

## 🔑 Demo Credentials

### For Assessors

**Map Access:**

- No login required for demo
- Navigate to: [http://127.0.0.1:8000/map/](http://127.0.0.1:8000/map/)
- Subscription requirement temporarily disabled (see `maps/views.py` lines 6-7)

**Admin Panel Access:**

- URL: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- Username: `demo_admin`
- Password: `Demo2026!`
- Permissions: View/edit schools and air quality data (staff user, not superuser)

**Subscription Page:**

- URL: [http://127.0.0.1:8000/subscriptions/](http://127.0.0.1:8000/subscriptions/)
- View Stripe integration (test mode)
- Note: Real Stripe test keys required for actual checkout

---

## 🛠 Technology Stack

### Backend

- **Python 3.13**
- **Django 6.0** - Web framework
- **PostgreSQL 17** - Primary database
- **TimescaleDB** - Time-series extension for sensor readings
- **psycopg2** - PostgreSQL adapter

### Frontend

- **Bootstrap 5** - Responsive UI framework
- **Leaflet.js** - Interactive mapping
- **Vanilla JavaScript** - Minimal client-side scripting

### APIs & Data Sources

- **London Air Quality Network (LAQN)** - Reference-grade monitoring stations
- **Breathe London via OpenAQ** - Calibrated low-cost sensors
- **LAEI 2022** - London Atmospheric Emissions Inventory (modelled baseline)

### Payment Processing

- **Stripe** - Subscription billing (£2.50/month)

### Testing

- **Django TestCase** - Unit and integration tests
- **Coverage.py** - Test coverage analysis

### Development Tools

- **python-decouple** - Environment variable management
- **Git** - Version control
- **GitHub** - Code repository

---

## 📦 Installation

### Prerequisites

- Python 3.13+
- PostgreSQL 17 with TimescaleDB extension
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/GavinKingcome/schools_air_quality_msp4.git
cd schools_air_quality_msp4
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up PostgreSQL + TimescaleDB

**Create Database:**

```sql
CREATE DATABASE schools_air_quality_db;
\c schools_air_quality_db
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

**Create Database User:**

```sql
CREATE USER your_username WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE schools_air_quality_db TO your_username;
```

### Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=schools_air_quality_db
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# API Keys
BREATHE_LONDON_API_KEY=your-api-key-here

# Stripe (optional for demo)
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
STRIPE_PRICE_ID=price_YOUR_PRICE_ID_HERE
```

**Generate Django Secret Key:**

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Step 6: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 7: Load Initial Data

**Import Schools:**

```bash
python manage.py import_schools data/schools.csv
```

**Sync Sensors:**

```bash
python manage.py sync_laqn_sensors
python manage.py sync_breathe_sensors
```

**Fetch Initial Readings:**

```bash
python manage.py fetch_laqn_readings
python manage.py fetch_breathe_readings
```

### Step 8: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

---

## ⚙️ Configuration

### Database Settings

Located in `schools_air_quality_msp4/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}
```

### API Configuration

**Breathe London:**

- Register at [Breathe London Portal](https://www.breathelondon.org/)
- Request API key (2-3 day approval time)
- Add key to `.env` as `BREATHE_LONDON_API_KEY`

**LAQN:**

- No API key required
- Public endpoint: `https://api.erg.ic.ac.uk/AirQuality/`

### Stripe Configuration (Optional)

For testing subscription checkout:

1. Create account at [stripe.com](https://stripe.com)
2. Get test API keys from dashboard
3. Create product "Air Quality Dashboard Access" at £2.50/month
4. Add keys to `.env`
5. Uncomment `@subscription_required` decorator in `maps/views.py` (lines 6-7)

---

## 🚀 Running the Application

### Development Server

```bash
python manage.py runserver
```

Access at: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### Automated Data Updates

Set up cron jobs for hourly data fetching:

```bash
crontab -e
```

Add these lines:

```cron
# Fetch LAQN readings every hour at :05
5 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py fetch_laqn_readings >> /tmp/laqn_cron.log 2>&1

# Fetch Breathe London readings every hour at :10
10 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py fetch_breathe_readings >> /tmp/breathe_cron.log 2>&1
```

---

## 📊 Data Management

### Management Commands

**Schools:**

```bash
# Import schools from CSV
python manage.py import_schools data/schools.csv

# List schools
python manage.py shell -c "from schools.models import School; print(School.objects.count())"
```

**Sensors:**

```bash
# Sync LAQN sensors
python manage.py sync_laqn_sensors

# Sync Breathe London sensors
python manage.py sync_breathe_sensors

# Check sensor count
python manage.py shell -c "from air_quality.models import Sensor; print(f'Total: {Sensor.objects.count()}, Active: {Sensor.objects.filter(is_active=True).count()}')"
```

**Readings:**

```bash
# Fetch latest readings
python manage.py fetch_laqn_readings
python manage.py fetch_breathe_readings

# Check reading count
python manage.py shell -c "from air_quality.models import Reading; print(Reading.objects.count())"
```

### Data Sources

**LAEI 2022 (Baseline):**

- 20m × 20m grid modelled pollution concentrations
- Imported from Greater London Authority open data
- Provides baseline NO₂, NOx, PM2.5, PM10 for each school

**LAQN (Reference-Grade):**

- 16 stations in Lambeth/Southwark
- Hourly validated readings
- Used for adjustment factors

**Breathe London:**

- 26 calibrated sensors in study area
- Direct readings for schools within 150m
- Urban background site type only

---

## 🧪 Testing

### Run All Tests

```bash
python manage.py test
```

### Run Specific Test Files

```bash
python manage.py test schools.tests
python manage.py test air_quality.tests
python manage.py test maps.tests
python manage.py test subscriptions.tests
```

### Test Coverage

```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

**Current Status:** 31/39 tests passing (8 trivial assertion mismatches documented in test files)

---

## 📁 Project Structure

```
schools_air_quality_msp4/
├── air_quality/              # Air quality data app
│   ├── models.py            # Sensor, Reading, SensorAnnualStats
│   ├── services/            # API integration services
│   │   ├── breathe_london_api.py
│   │   └── laqn_api.py
│   ├── management/commands/ # Data fetching commands
│   └── tests.py
├── schools/                  # Schools app
│   ├── models.py            # School model with pollution data
│   ├── admin.py
│   └── tests.py
├── maps/                     # Map visualization app
│   ├── views.py             # Map view with school data
│   ├── templates/maps/
│   │   └── map.html         # Leaflet map interface
│   └── tests.py
├── subscriptions/           # Stripe subscription app
│   ├── models.py            # Subscription, Payment models
│   ├── views.py             # Checkout, webhooks
│   ├── decorators.py        # @subscription_required
│   ├── templates/subscriptions/
│   └── admin.py
├── docs/                     # Documentation
│   ├── database_schema.dbml # ERD (use dbdiagram.io)
│   ├── USER_STORIES.md      # Agile user stories
│   └── WIREFRAMES.md        # UI wireframes
├── static/                   # Static assets
│   ├── css/
│   └── js/
├── templates/               # Base templates
│   ├── base.html
│   └── registration/
│       └── login.html
├── .env                     # Environment variables (not in git)
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

---

## 📚 Documentation

Additional documentation available in `/docs/`:

- **[Database Schema (ERD)](docs/database_schema.dbml)** - Entity-Relationship Diagram (view at [dbdiagram.io](https://dbdiagram.io))
- **[User Stories](docs/USER_STORIES.md)** - 18 user stories with implementation status
- **[Wireframes](docs/WIREFRAMES.md)** - UI/UX wireframes for all key pages

---

## 🔒 Security Notes

### For Assessors

**Demo Mode:**

- `@subscription_required` decorator commented out in `maps/views.py` (lines 6-7)
- Allows free access to map for evaluation purposes
- In production, uncomment decorator to enforce subscription

**API Key Management:**

- Breathe London API key in `.env` - keep confidential
- Django `SECRET_KEY` rotated for security
- Stripe keys use test mode (pk*test*_, sk*test*_)

**Lessons Learned:**

- ⚠️ `.env` was accidentally committed to git history (3 commits)
- ✅ Resolved by rotating SECRET_KEY immediately
- ✅ Breathe London key retained due to 2-3 day reapplication time
- ✅ `.gitignore` properly configured to prevent future exposure

### Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=False` in `.env`
- [ ] Use production Stripe keys (not test mode)
- [ ] Uncomment `@subscription_required` decorator
- [ ] Configure `ALLOWED_HOSTS` with actual domain
- [ ] Set up HTTPS/SSL certificates
- [ ] Enable PostgreSQL SSL connections
- [ ] Implement rate limiting on API endpoints
- [ ] Set up monitoring and error tracking
- [ ] Configure regular database backups
- [ ] Review and update CORS settings

---

## 🚧 Future Enhancements

### Phase 2 Features

1. **Tiered Pricing**
   - Free tier for parents/families (basic map view)
   - Paid tier for schools/administrators (£2.50/month, full features)

2. **Advanced Filtering**
   - Filter schools by pollution levels
   - Filter by school type (primary vs nursery)
   - Filter by borough

3. **Air Quality Alerts**
   - Email notifications when pollution exceeds thresholds
   - SMS alerts for critical air quality episodes
   - Recommended actions (keep children indoors, etc.)

4. **Historical Trends**
   - Interactive graphs showing pollution over time
   - Compare current year to previous years
   - Seasonal pattern analysis

5. **Data Export**
   - PDF reports for school governors
   - CSV downloads for researchers
   - API access for third-party integrations

6. **Accessibility**
   - Full WCAG 2.1 AA compliance
   - Screen reader optimization
   - High contrast mode

7. **Admin Dashboard**
   - Data quality metrics
   - API health monitoring
   - User analytics

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Gavin Kingcome**

- GitHub: [@GavinKingcome](https://github.com/GavinKingcome)
- Email: gavin@gavinkingcome.com

---

## 🙏 Acknowledgments

- **London Air Quality Network (LAQN)** - Reference-grade monitoring data
- **Breathe London** - Calibrated sensor network
- **Greater London Authority** - LAEI 2022 modelled data
- **OpenAQ** - Open air quality data platform
- **Code Institute** - Project supervision and guidance
- **GitHub Copilot** - AI-powered development assistance
- **William S. Vincent** - *Django for Beginners* - Foundational Django concepts and best practices

---

## 📞 Support

For questions or issues regarding this project:

1. Check existing documentation in `/docs/`
2. Review test files for usage examples
3. Contact: gavin@gavinkingcome.com

---

**Last Updated:** 29 January 2026
