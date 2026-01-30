# Heroku Deployment Guide

## Prerequisites

- Heroku account (free tier works)
- Heroku CLI installed: `brew install heroku/brew/heroku`
- Git repository

## Step-by-Step Deployment

### 1. Login to Heroku

```bash
heroku login
```

### 2. Create Heroku App

```bash
heroku create schools-air-quality-msp4
# Or use your preferred app name
```

### 3. Add PostgreSQL Database

```bash
heroku addons:create heroku-postgresql:essential-0
```

### 4. Set Environment Variables

```bash
# Django Secret Key
heroku config:set SECRET_KEY="your-production-secret-key-here"

# Debug mode (set to False for production)
heroku config:set DEBUG=False

# Allowed hosts (use your Heroku app URL)
heroku config:set ALLOWED_HOSTS="schools-air-quality-msp4.herokuapp.com,localhost"

# API Keys
heroku config:set BREATHE_LONDON_API_KEY="your-key-here"

# Stripe Keys (test mode)
heroku config:set STRIPE_PUBLISHABLE_KEY="your-stripe-pk-test-key"
heroku config:set STRIPE_SECRET_KEY="your-stripe-sk-test-key"
heroku config:set STRIPE_WEBHOOK_SECRET="your-stripe-webhook-secret"
heroku config:set STRIPE_PRICE_ID="your-stripe-price-id"
```

### 5. Deploy to Heroku

```bash
git push heroku main
```

### 6. Run Migrations

```bash
heroku run python manage.py migrate
```

### 7. Create Superuser

```bash
heroku run python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
heroku run python manage.py collectstatic --noinput
```

### 9. Open Your App

```bash
heroku open
```

## Post-Deployment Setup

### Load School Data

```bash
# If you have a fixture file
heroku run python manage.py loaddata schools

# Or load LAEI data
heroku run python manage.py load_laei_data
```

### Fetch Sensor Data

```bash
heroku run python manage.py fetch_laqn_data
heroku run python manage.py fetch_breathe_london_data
```

### Set Up Scheduler (Optional)

```bash
# Add Heroku Scheduler
heroku addons:create scheduler:standard

# Open scheduler dashboard
heroku addons:open scheduler

# Add hourly job: python manage.py fetch_laqn_data
# Add hourly job: python manage.py fetch_breathe_london_data
```

## Verify Deployment

1. Open your app: https://schools-air-quality-msp4.herokuapp.com/map/
2. Test map display with school markers
3. Test admin access: https://schools-air-quality-msp4.herokuapp.com/admin/
4. Check logs: `heroku logs --tail`

## Troubleshooting

### View Logs

```bash
heroku logs --tail
```

### Restart App

```bash
heroku restart
```

### Check Database

```bash
heroku pg:info
```

### Run Django Shell

```bash
heroku run python manage.py shell
```

## Important Notes

1. **Static Files**: Whitenoise handles static files (already configured)
2. **Database**: PostgreSQL provided by Heroku (no TimescaleDB on free tier)
3. **Environment**: All sensitive data in environment variables (not in code)
4. **Debug Mode**: Always set DEBUG=False in production
5. **HTTPS**: Heroku provides free HTTPS

## Files Required for Deployment

✅ **Procfile** - Tells Heroku how to run the app
✅ **requirements.txt** - Python dependencies
✅ **runtime.txt** - Python version
✅ **settings.py** - Already configured with environment variables

## Screenshot Documentation

After successful deployment:

1. Take screenshot of deployed site at `/map/`
2. Save as `docs/screenshots/heroku-deployed.png`
3. Add to TESTING.md or ASSESSOR_NOTES.md

---

**Deployed URL**: https://schools-air-quality-msp4.herokuapp.com
