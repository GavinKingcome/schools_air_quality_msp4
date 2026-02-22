"""
Celery tasks for fetching air quality sensor data.

These tasks run periodically (scheduled by Celery Beat) to keep the
database updated with fresh sensor readings from LAQN and Breathe London.

Tasks are configured in schools_air_quality_msp4/celery.py:
- fetch_laqn_readings_task: Runs hourly at :05
- fetch_breathe_readings_task: Runs hourly at :10

Retries are automatic if API calls fail (network issues, API downtime).
"""

from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),  # Retry on any exception
    retry_kwargs={'max_retries': 3, 'countdown': 300},  # 3 retries, 5 min apart
    retry_backoff=True,  # Exponential backoff between retries
)
def fetch_laqn_readings_task(self):
    """
    Fetch latest readings from LAQN sensors.
    
    Runs the fetch_laqn_readings management command to pull the last
    2 hours of data from LAQN API.
    
    Retries:
        - Max 3 retries on failure
        - 5 minute intervals with exponential backoff
        - Useful for handling temporary API outages
    
    Returns:
        dict: Summary of fetch operation (readings created, sensors updated)
    """
    try:
        logger.info("Starting LAQN readings fetch (Celery task)")
        
        # Call the management command
        # This is the same as: python manage.py fetch_laqn_readings
        call_command('fetch_laqn_readings', hours=2)
        
        logger.info("LAQN readings fetch completed successfully")
        return {'status': 'success', 'source': 'LAQN'}
        
    except Exception as e:
        logger.error(f"LAQN fetch failed: {e}")
        # Exception will be caught by autoretry_for
        raise


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 300},
    retry_backoff=True,
)
def fetch_breathe_readings_task(self):
    """
    Fetch latest readings from Breathe London sensors.
    
    Runs the fetch_breathe_readings management command to pull the last
    2 hours of data from Breathe London API via OpenAQ.
    
    Retries:
        - Max 3 retries on failure
        - 5 minute intervals with exponential backoff
        - Handles API rate limits and temporary failures
    
    Returns:
        dict: Summary of fetch operation (readings created, sensors updated)
    """
    try:
        logger.info("Starting Breathe London readings fetch (Celery task)")
        
        # Call the management command
        # This is the same as: python manage.py fetch_breathe_readings
        call_command('fetch_breathe_readings', hours=2)
        
        logger.info("Breathe London readings fetch completed successfully")
        return {'status': 'success', 'source': 'Breathe London'}
        
    except Exception as e:
        logger.error(f"Breathe London fetch failed: {e}")
        # Exception will be caught by autoretry_for
        raise


# Additional tasks for future expansion

@shared_task
def calculate_school_air_quality_task(school_id):
    """
    Calculate current air quality for a specific school.
    
    This could be expanded to pre-calculate and cache air quality
    readings for all schools, improving map load performance.
    
    Args:
        school_id (int): Primary key of school to calculate
    """
    from schools.models import School
    
    try:
        school = School.objects.get(id=school_id)
        reading = school.get_current_reading()
        
        logger.info(f"Calculated air quality for {school.name}: {reading['method']}")
        return reading
        
    except School.DoesNotExist:
        logger.error(f"School {school_id} not found")
        return None


@shared_task
def sync_sensors_task():
    """
    Sync sensor lists from LAQN and Breathe London APIs.
    
    This task could run daily to discover new sensors or update
    sensor metadata (location, status, etc.).
    
    Currently not scheduled - would need to be added to beat_schedule
    in celery.py if needed.
    """
    try:
        logger.info("Starting sensor sync")
        
        call_command('sync_laqn_sensors')
        call_command('sync_breathe_sensors')
        
        logger.info("Sensor sync completed successfully")
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f"Sensor sync failed: {e}")
        raise
