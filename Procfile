web: gunicorn schools_air_quality_msp4.wsgi --log-file -
worker: celery -A schools_air_quality_msp4 worker --loglevel=info
beat: celery -A schools_air_quality_msp4 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
