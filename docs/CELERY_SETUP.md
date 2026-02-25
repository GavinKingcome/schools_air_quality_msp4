# Celery Setup Guide - Early Years Schools Pollution Monitor

## Overview

Celery is configured to automatically fetch fresh sensor data from LAQN and Breathe London APIs every hour, ensuring users always see current air quality readings.

**Architecture:**

```
Django App ──► Redis (Message Broker) ──► Celery Worker
                  ▲                            │
                  │                            │
            Celery Beat ◄───────────────────────┘
            (Scheduler)
```

- **Celery Beat**: Scheduler that triggers tasks at specified times
- **Redis**: Message broker that holds the task queue
- **Celery Worker**: Executes tasks in the background
- **Django App**: Your web application

---

## Files Created

### 1. `schools_air_quality_msp4/celery.py`

Main Celery configuration file that:

- Connects Celery to Django
- Configures Redis as message broker
- Defines periodic task schedule (hourly at :05 and :10)
- Sets task timeouts and retry policies

### 2. `air_quality/tasks.py`

Celery task definitions:

- `fetch_laqn_readings_task()` - Fetches LAQN sensor data
- `fetch_breathe_readings_task()` - Fetches Breathe London data
- Both tasks have automatic retry on failure (3 retries, 5 min apart)

### 3. `schools_air_quality_msp4/__init__.py` (Updated)

Imports Celery app when Django starts, ensuring tasks are discovered

### 4. `schools_air_quality_msp4/settings.py` (Updated)

- Added `django_celery_beat` to INSTALLED_APPS
- Configured Redis connection
- Set timezone to Europe/London

### 5. `Procfile` (Updated)

Defines three Heroku processes:

- `web`: Django web server
- `worker`: Celery worker
- `beat`: Celery beat scheduler

---

## Local Development

### Prerequisites

1. **Install Redis** (if not already installed):

   ```bash
   # macOS
   brew install redis
   brew services start redis

   # Or manually:
   redis-server
   ```

2. **Verify Python packages installed**:

   ```bash
   source venv/bin/activate
   pip list | grep -E "(celery|redis|django-celery-beat)"
   ```

   Should show:
   - celery==5.3.6
   - django-celery-beat==2.5.0
   - redis==5.0.1

### Running Celery Locally

You need **3 terminal windows** running simultaneously:

**Terminal 1 - Django Development Server:**

```bash
cd /path/to/schools_air_quality_msp4
source venv/bin/activate
python manage.py runserver
```

**Terminal 2 - Celery Worker:**

```bash
cd /path/to/schools_air_quality_msp4
source venv/bin/activate
celery -A schools_air_quality_msp4 worker --loglevel=info
```

**Terminal 3 - Celery Beat (Scheduler):**

```bash
cd /path/to/schools_air_quality_msp4
source venv/bin/activate
celery -A schools_air_quality_msp4 beat --loglevel=info
```

### Testing Celery Tasks Manually

You can trigger tasks immediately without waiting for the schedule:

```bash
# In Django shell
python manage.py shell

>>> from air_quality.tasks import fetch_laqn_readings_task, fetch_breathe_readings_task
>>>
>>> # Run task synchronously (blocks until complete)
>>> fetch_laqn_readings_task()
>>>
>>> # Or run asynchronously (returns immediately)
>>> result = fetch_breathe_readings_task.delay()
>>> result.status  # Check status
>>> result.get()   # Wait for result
```

### Monitoring Tasks

View task execution in real-time:

- **Worker terminal**: Shows tasks being executed
- **Beat terminal**: Shows scheduled tasks being sent to queue
- **Django logs**: Shows actual data fetch results

---

## Heroku Deployment

### 1. Add Heroku Redis Addon

Celery requires Redis as a message broker:

```bash
# Navigate to your project
cd /path/to/schools_air_quality_msp4

# Add Redis addon (mini tier is free for hobbyists)
heroku addons:create heroku-redis:mini -a schools-air-quality-msp4

# Verify Redis URL is set
heroku config:get REDIS_URL -a schools-air-quality-msp4
```

The addon automatically sets a `REDIS_URL` environment variable that your Django settings will use.

### 2. Deploy Updated Code

```bash
# Commit Celery changes
git add .
git commit -m "Add Celery for automated sensor data fetching"

# Push to Heroku
git push heroku main

# Run migrations for django_celery_beat
heroku run python manage.py migrate -a schools-air-quality-msp4
```

### 3. Scale Up Worker and Beat Processes

By default, new processes are disabled. Enable them:

```bash
# Start 1 worker dyno
heroku ps:scale worker=1 -a schools-air-quality-msp4

# Start 1 beat dyno
heroku ps:scale beat=1 -a schools-air-quality-msp4

# Verify all processes running
heroku ps -a schools-air-quality-msp4
```

You should see:

- `web.1`: running (your Django app)
- `worker.1`: running (Celery worker)
- `beat.1`: running (Celery beat scheduler)

### 4. Monitor Celery Logs

```bash
# View all logs
heroku logs --tail -a schools-air-quality-msp4

# View only worker logs
heroku logs --tail --ps worker -a schools-air-quality-msp4

# View only beat logs
heroku logs --tail --ps beat -a schools-air-quality-msp4
```

Look for messages like:

```
[worker] Task air_quality.tasks.fetch_laqn_readings_task succeeded
[beat] Scheduler: Sending due task fetch-laqn-readings-hourly
```

---

## Task Schedule

Tasks run automatically on this schedule:

| Task                          | Schedule          | Purpose                       |
| ----------------------------- | ----------------- | ----------------------------- |
| `fetch_laqn_readings_task`    | Every hour at :05 | Fetch LAQN sensor readings    |
| `fetch_breathe_readings_task` | Every hour at :10 | Fetch Breathe London readings |

This ensures:

- Fresh data every hour
- LAQN and Breathe fetches are staggered (reduces API load)
- Tasks expire if they take too long (prevent queue buildup)

---

## Troubleshooting

### Worker Not Processing Tasks

**Check Redis connection:**

```bash
heroku run python manage.py shell -a schools-air-quality-msp4

>>> import redis
>>> from django.conf import settings
>>> r = redis.from_url(settings.CELERY_BROKER_URL)
>>> r.ping()  # Should return True
```

**Restart worker:**

```bash
heroku ps:restart worker -a schools-air-quality-msp4
```

### Tasks Failing

**View errors in logs:**

```bash
heroku logs --tail --ps worker -a schools-air-quality-msp4 | grep ERROR
```

**Check task retry attempts:**

- Tasks automatically retry 3 times
- 5 minute intervals between retries
- Exponential backoff (5min, 10min, 20min)

### Beat Not Scheduling Tasks

**Verify beat is running:**

```bash
heroku ps -a schools-air-quality-msp4
```

**Check beat logs:**

```bash
heroku logs --tail --ps beat -a schools-air-quality-msp4
```

Should see:

```
DatabaseScheduler: Schedule changed.
Scheduler: Sending due task fetch-laqn-readings-hourly
```

---

## Cost Considerations

### Heroku Dyno Usage

- **web**: Required (you already have this)
- **worker**: Required for Celery ($7/month for basic dyno)
- **beat**: Required for scheduling ($7/month for basic dyno)
- **redis**: Free mini tier includes with Heroku Redis addon

**Total additional cost**: ~$14/month for automated data updates

### Alternative: Heroku Scheduler (Cheaper but Less Robust)

If budget is tight, you can use Heroku Scheduler instead (free):

````bash
# Add scheduler addon
heroku addons:create scheduler:standard -a schools-air-quality-msp4

# Configure in Heroku dashboard:
# 1. Go to Resources → Heroku Scheduler → Open
# 2. Add job: python manage.py fetch_laqn_readings (hourly at :05)
# 3. Add job: python manage.py fetch_breathe_readings (hourly at :10)
``
`

**Downsides of Scheduler:**
- No retry logic
- No monitoring
- Can skip runs if dyno is busy
- Not suitable for production at scale

---

## Scaling to All London Boroughs

When expanding to all 33 boroughs (~400 schools, ~100 sensors):

**Adjust task frequency:**
```python
# In schools_air_quality_msp4/celery.py

app.conf.beat_schedule = {
    'fetch-laqn-readings': {
        'task': 'air_quality.tasks.fetch_laqn_readings_task',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    'fetch-breathe-readings': {
        'task': 'air_quality.tasks.fetch_breathe_readings_task',
        'schedule': crontab(minute='5,35'),  # Offset from LAQN
    },
}
````

**Scale workers:**

```bash
# Add more workers for parallel processing
heroku ps:scale worker=2 -a schools-air-quality-msp4
```

**Monitor Redis usage:**

```bash
heroku addons:info heroku-redis -a schools-air-quality-msp4
```

May need to upgrade Redis tier if hitting memory limits.

---

## Next Steps

1. ✅ Celery is now configured and ready
2. Deploy to Heroku and enable worker/beat dynos
3. Monitor logs for first hour to verify tasks run
4. Check database to confirm fresh readings arrive
5. Test that Oliver Goldsmith shows "Direct sensor reading" after fetch

---

## Additional Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Django Celery Beat](https://django-celery-beat.readthedocs.io/)
- [Heroku Redis](https://devcenter.heroku.com/articles/heroku-redis)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#tips-and-best-practices)
