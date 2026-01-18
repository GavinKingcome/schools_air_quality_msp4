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
from air_quality.services.breathe_london_api import BreatheLondonApi, PARAMETER_MAP
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
                # Get OpenAQ location ID from metadata
                openaq_id = sensor.metadata.get('openaq_id')
                if not openaq_id:
                    logger.warning(f'No OpenAQ ID for sensor {sensor.site_code}')
                    continue
                
                # Fetch latest measurements
                measurements = api.get_latest_measurements(
                    location_id=openaq_id,
                    parameters=list(PARAMETER_MAP.keys())
                )
                
                if not measurements:
                    continue
                
                # Process measurements - group by timestamp
                readings_by_time = {}
                
                for result in measurements:
                    # Handle nested structure from latest endpoint
                    for measurement in result.get('measurements', [result]):
                        param = measurement.get('parameter', '')
                        if param not in PARAMETER_MAP:
                            continue
                        
                        value = measurement.get('value')
                        timestamp_str = measurement.get('date', {}).get('utc') or measurement.get('datetime')
                        
                        if value is None or timestamp_str is None:
                            continue
                        
                        # Parse timestamp
                        try:
                            if isinstance(timestamp_str, str):
                                # Handle various ISO formats
                                timestamp_str = timestamp_str.replace('Z', '+00:00')
                                from datetime import datetime
                                timestamp = datetime.fromisoformat(timestamp_str)
                            else:
                                timestamp = timestamp_str
                        except (ValueError, TypeError) as e:
                            logger.warning(f'Could not parse timestamp {timestamp_str}: {e}')
                            continue
                        
                        # Round to hour for grouping
                        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                        
                        if hour_key not in readings_by_time:
                            readings_by_time[hour_key] = {}
                        
                        readings_by_time[hour_key][PARAMETER_MAP[param]] = value
                
                # Create readings
                for timestamp, values in readings_by_time.items():
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
