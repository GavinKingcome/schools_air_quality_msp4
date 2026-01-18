"""
Django management command to fetch LAQN readings.

Usage:
    python manage.py fetch_laqn_readings
    python manage.py fetch_laqn_readings --hours=24
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from air_quality.models import Sensor, Reading
from air_quality.services.laqn_api import LAQNApi
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


SPECIES_MAP = {
    'NO2': 'no2',
    'PM25': 'pm25',
    'PM10': 'pm10',
    'O3': 'o3',
    'NOX': 'nox',
}


class Command(BaseCommand):
    help = 'Fetch latest readings from LAQN sensors'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=2,
            help='Hours of historical data to fetch (default: 2)'
        )
        parser.add_argument(
            '--sensor',
            type=str,
            help='Fetch for specific sensor site_code only'
        )
    
    def handle(self, *args, **options):
        api = LAQNApi()
        hours = options['hours']
        
        # Get LAQN sensors
        if options['sensor']:
            sensors = Sensor.objects.filter(
                site_code=options['sensor'],
                network='LAQN',
                is_active=True
            )
        else:
            sensors = Sensor.objects.filter(
                network='LAQN',
                is_active=True
            )
        
        if not sensors.exists():
            self.stdout.write('No active LAQN sensors found.')
            return
        
        self.stdout.write(f'Fetching readings for {sensors.count()} LAQN sensors...')
        
        start_date = datetime.now() - timedelta(hours=hours)
        end_date = datetime.now()
        
        readings_created = 0
        sensors_updated = 0
        errors = 0
        
        for sensor in sensors:
            try:
                raw_readings = api.get_hourly_readings(
                    site_code=sensor.site_code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Group by timestamp
                by_time = {}
                for r in raw_readings:
                    ts_str = r.get('timestamp')
                    species = r.get('species')
                    value = r.get('value')
                    
                    if not all([ts_str, species]):
                        continue
                    
                    # Parse timestamp
                    try:
                        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        ts = timezone.make_aware(ts, timezone.utc)
                    except ValueError:
                        continue
                    
                    if ts not in by_time:
                        by_time[ts] = {}
                    
                    if species in SPECIES_MAP and value:
                        try:
                            by_time[ts][SPECIES_MAP[species]] = float(value)
                        except ValueError:
                            pass
                
                # Create readings
                for timestamp, values in by_time.items():
                    if not values:
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
                logger.error(f'Error fetching {sensor.site_code}: {e}')
                errors += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nFetch complete: {readings_created} readings created '
                f'from {sensors_updated} sensors ({errors} errors)'
            )
        )
