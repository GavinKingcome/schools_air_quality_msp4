"""
Django management command to fetch Breathe London readings.

Usage:
    python manage.py fetch_breathe_readings
    python manage.py fetch_breathe_readings --hours=6

Schedule this to run hourly via cron or Celery.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from air_quality.models import Sensor, Reading
from air_quality.services.breathe_london_api import BreatheLondonApi
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch latest readings from Breathe London sensors'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='Hours of data to fetch (default: 2)'
        )
        parser.add_argument(
            '--sensor',
            type=str,
            help='Fetch for specific sensor site_code only'
        )
    
    def handle(self, *args, **options):
        api_key = getattr(settings, 'BREATHE_LONDON_API_KEY', None)
        
        if not api_key:
            self.stderr.write(
                self.style.ERROR('BREATHE_LONDON_API_KEY not found in settings')
            )
            return
        
        api = BreatheLondonApi(api_key)
        hours = options['hours']
        
        # Get Breathe London sensors
        if options['sensor']:
            sensors = Sensor.objects.filter(
                site_code=options['sensor'],
                network='BREATHE',
                is_active=True
            )
        else:
            sensors = Sensor.objects.filter(
                network='BREATHE',
                is_active=True
            )
        
        if not sensors.exists():
            self.stdout.write('No active Breathe London sensors found. Run sync_breathe_sensors first.')
            return
        
        self.stdout.write(f'Fetching readings for {sensors.count()} sensors...')
        
        readings_created = 0
        sensors_updated = 0
        errors = 0
        
        for sensor in sensors:
            try:   
                # Calculate time range
                end_time = timezone.now()
                start_time = end_time - timedelta(hours=hours)
                
                # Fetch sensor data from Breathe London API
                sensor_data = api.get_sensor_data(
                    site_code=sensor.site_code,  # Use sensor.site_code (e.g., "BL0001")
                    start_time=start_time,
                    end_time=end_time 
                )
                
                
                if not sensor_data:
                    continue
                
                # Process readings - group by timestamp
                readings_by_time = {}
                
                for data_point in sensor_data:
                    timestamp_str = data_point.get('DateTime')
                    if not timestamp_str:
                        continue
                    
                    # Parse timestamp
                    try:
                        from datetime import datetime
                        # Expected format: "2026-01-25T10:00:00Z" or similar
                        timestamp_str = timestamp_str.replace('Z', '+00:00')
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timezone.is_naive(timestamp):
                            timestamp = timezone.make_aware(timestamp)
                    except (ValueError, TypeError) as e:
                        logger.warning(f'Could not parse timestamp {timestamp_str}: {e}')
                        continue
                    
                    # Round to hour for grouping
                    hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                    
                    if hour_key not in readings_by_time:
                        readings_by_time[hour_key] = {}
                    
                    # Extract pollutant value using Species and ScaledValue fields
                    species = data_point.get('Species')
                    value = data_point.get('ScaledValue')
                    
                    if value is not None:
                        if species == 'NO2':
                            readings_by_time[hour_key]['no2'] = float(value)
                        elif species == 'PM2.5':
                            readings_by_time[hour_key]['pm25'] = float(value)
                        elif species == 'PM10':
                            readings_by_time[hour_key]['pm10'] = float(value)
                
                # Create readings
                for timestamp, values in readings_by_time.items():
                    if not values:  # Skip empty readings
                        continue
                        
                    reading, created = Reading.objects.update_or_create(
                        sensor=sensor,
                        timestamp=timestamp,
                        defaults={
                            'no2': values.get('no2'),
                            'pm25': values.get('pm25'),
                            'pm10': values.get('pm10'),
                            'o3': values.get('o3'),
                            'nox': values.get('nox'),
                        }
                    )
                    if created:
                        readings_created += 1
                
                sensors_updated += 1
                
            except Exception as e:
                logger.error(f'Error fetching data for {sensor.site_code}: {e}')
                errors += 1
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nFetch complete: {readings_created} readings created '
                f'from {sensors_updated} sensors ({errors} errors)'
            )
        )
