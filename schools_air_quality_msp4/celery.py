"""
Celery configuration for Early Years Schools Pollution Monitor.

This module sets up Celery for asynchronous task processing and periodic
task scheduling. It handles:
- Hourly sensor data fetching from LAQN and Breathe London APIs
- Background processing of air quality calculations
- Scheduled data updates for real-time school air quality monitoring

For local development:
    celery -A schools_air_quality_msp4 worker -l info
    celery -A schools_air_quality_msp4 beat -l info

For production on Heroku:
    - Worker runs as separate dyno (see Procfile)
    - Uses Redis as message broker (Heroku Redis addon)
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')

# Create Celery app
app = Celery('schools_air_quality_msp4')

# Load config from Django settings with CELERY_ prefix
# Example: CELERY_BROKER_URL in settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed Django apps
# Looks for tasks.py in each app
app.autodiscover_tasks()


# Periodic task schedule
app.conf.beat_schedule = {
    'fetch-laqn-readings-hourly': {
        'task': 'air_quality.tasks.fetch_laqn_readings_task',
        'schedule': crontab(minute=5),  # Every hour at :05
        'options': {'expires': 3600}  # Task expires after 1 hour
    },
    'fetch-breathe-readings-hourly': {
        'task': 'air_quality.tasks.fetch_breathe_readings_task',
        'schedule': crontab(minute=10),  # Every hour at :10
        'options': {'expires': 3600}  # Task expires after 1 hour
    },
}

# Celery configuration
app.conf.update(
    # Time zone for scheduled tasks
    timezone='Europe/London',
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task time limits (safety)
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=900,  # 15 minutes hard limit
    
    # Retry configuration
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Retry if worker dies
    
    # Result backend (optional - stores task results)
    result_backend='redis://localhost:6379/0',
    result_expires=3600,  # Keep results for 1 hour
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')
