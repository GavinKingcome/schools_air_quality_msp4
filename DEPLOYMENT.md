# Heroku Deployment Guide

## Deployment Success! 🎉

![Deployed Application on Heroku](screenshots/heroku-deployed.png)

**Live URL:** https://schools-air-quality-msp4-39fe66170249.herokuapp.com/map/

---

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
heroku config:set ALLOWED_HOSTS="schools-air-quality-msp4-39fe66170249.herokuapp.com,localhost"

# API Keys
heroku config:set BREATHE_LONDON_API_KEY="your-key-here"
heroku config:set CARTO_API_KEY="your-carto-key-here"

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
1. Open your app: https://schools-air-quality-msp4-39fe66170249.herokuapp.com/map/
2. Test map display with school markers
3. Test admin access: https://schools-air-quality-msp4-39fe66170249.herokuapp.com/admin/
4. Check logs: `heroku logs --tail`

```bash
heroku open
```

## Post-Deployment Setup

Run these after the first deploy, and again after any deploy that changes the data or the models. Each `heroku run` starts a one-off copy of the app on Heroku and runs a single command. Where a command has `--dry-run`, run that first and check the output.

For what each command does and how they fit together, see `docs/HOW_IT_WORKS.md`.

### Load Schools and Childcare

```bash
# Give the schools already on the live site their URNs,
# so the import updates them instead of adding duplicates
heroku run python manage.py backfill_school_urns dev/schools_processed.csv

# Schools (GIAS) and childcare settings (Ofsted), with their LAEI 2022 values
heroku run python manage.py import_schools data/southwark_lambeth_schools.csv
heroku run python manage.py import_childcare data/southwark_lambeth_childcare.csv
```

The two CSV files in `data/` come from `build_slice.py` in the `school-pollution-analyses` repo.

### Set Up the Sensors

Run these in order: the annual averages need the sensor lists, and `assign_sensors` needs both readings and averages.

```bash
# 1. Sensor lists
heroku run python manage.py sync_laqn_sensors
heroku run python manage.py sync_breathe_sensors
# heroku run python manage.py sync_aqe_sensors    # once the Air Quality England site is back

# 2. Readings from the last 48 hours
heroku run python manage.py fetch_all_readings --hours=48

# 3. Annual averages
#    LAQN and AQE: the last calendar year
heroku run python manage.py fetch_annual_stats
#    Breathe London: the last 12 full months (takes a few minutes)
heroku run python manage.py fetch_breathe_annual_stats --dry-run
heroku run python manage.py fetch_breathe_annual_stats

# 4. Which sensor each school uses
heroku run python manage.py assign_sensors --dry-run
heroku run python manage.py assign_sensors
```

### Set Up the Scheduler

The live site needs its own schedule, so readings keep arriving whether or not any computer is switched on.

```bash
# Add Heroku Scheduler (first time only)
heroku addons:create scheduler:standard

# Open the scheduler dashboard
heroku addons:open scheduler
```

In the dashboard, add two jobs:

| Frequency | Job |
|---|---|
| Every hour at :00 | `python manage.py fetch_all_readings --hours=48` |
| Every hour at :10 | `python manage.py assign_sensors` |

The fetch looks back 48 hours on every run, so readings that a network publishes late are still collected. Readings already saved are left alone. The assign job runs 10 minutes later, so it sees the newest readings.

**Remove any old jobs** in the dashboard that run `fetch_laqn_data` or `fetch_breathe_london_data`. Those commands no longer exist.

**Use the Scheduler or Celery, not both.** The Procfile also defines Celery `worker` and `beat` processes. If they are switched on, they run their own, older fetch tasks as well. Check with `heroku ps`, and switch them off with:

```bash
heroku ps:scale worker=0 beat=0
```

Scheduler jobs run on one-off dynos, which count towards the account's dyno usage.

### Jobs to Run by Hand

| How often | Command | Why |
|---|---|---|
| About once a month | `heroku run python manage.py fetch_breathe_annual_stats` | The Breathe London averages cover a rolling 12 months |
| Each January | `heroku run python manage.py fetch_annual_stats` | LAQN and AQE averages for the year just ended |
| When sensors may have changed | `heroku run python manage.py sync_laqn_sensors` and `sync_breathe_sensors` | Picks up new and closed sensors |

## Verify Deployment

1. Open your app: https://schools-air-quality-msp4-39fe66170249.herokuapp.com/map/
2. Test map display with school markers, and open a few school popups
3. Test admin access: https://schools-air-quality-msp4-39fe66170249.herokuapp.com/admin/
4. Check logs: `heroku logs --tail`
5. After the first scheduled runs, check the scheduler jobs worked: `heroku logs --source app --tail` while a job runs, or the job's "Last run" in the dashboard

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

### Check Which Processes Are Running

```bash
heroku ps
```

## Important Notes

1. **Static Files**: Whitenoise handles static files (already configured)
2. **Database**: PostgreSQL provided by Heroku (no TimescaleDB on free tier). It is separate from the local database used in development.
3. **Environment**: All sensitive data in environment variables (not in code)
4. **Debug Mode**: Always set DEBUG=False in production
5. **HTTPS**: Heroku provides free HTTPS

## Files Required for Deployment

✅ **Procfile** - Tells Heroku how to run the app
✅ **requirements.txt** - Python dependencies
✅ **.python-version** - Python version
✅ **settings.py** - Already configured with environment variables

## Screenshot Documentation

After successful deployment:

1. Take screenshot of deployed site at `/map/`
2. Save as `docs/screenshots/heroku-deployed.png`
3. Add to TESTING.md or ASSESSOR_NOTES.md

---

**Deployed URL**: https://schools-air-quality-msp4-39fe66170249.herokuapp.com/map/
