"""
Fetch hourly air quality data from Breathe London sensors.

Usage:
    python manage.py fetch_breathe_london_data
    python manage.py fetch_breathe_london_data --hours 48
"""

import requests
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from schools.models import Sensor, Reading


class Command(BaseCommand):
    help = 'Fetch hourly readings from Breathe London sensors'
    
    # Breathe London API (uses Google Cloud)
    BASE_URL = 'https://api.breathelondon.org/api'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to fetch (default: 24)'
        )
    
    def handle(self, *args, **options):
        # Check API key
        api_key = settings.BREATHE_LONDON_API_KEY
        if not api_key:
            self.stdout.write(
                self.style.ERROR('BREATHE_LONDON_API_KEY not configured in .env')
            )
            return
        
        hours = options['hours']
        
        # Get active Breathe London sensors
        sensors = Sensor.objects.filter(network='BREATHE', is_active=True)
        
        if not sensors.exists():
            self.stdout.write(self.style.WARNING('No active Breathe London sensors found'))
            return
        
        end_date = timezone.now()
        start_date = end_date - timedelta(hours=hours)
        
        self.stdout.write(f'Fetching data from {start_date} to {end_date}...')
        
        headers = {
            'X-API-Key': api_key
        }
        
        total_created = 0
        
        for sensor in sensors:
            self.stdout.write(f'Processing {sensor.site_code} - {sensor.name}...')
            
            # Fetch readings
            created = self._fetch_sensor_readings(
                sensor,
                start_date,
                end_date,
                headers
            )
            total_created += created
            
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ {created} readings imported')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal: {total_created} readings imported')
        )
    
    def _fetch_sensor_readings(self, sensor, start_date, end_date, headers):
        """Fetch readings for one sensor."""
        
        # API endpoint structure (adjust based on actual Breathe London API docs)
        url = f'{self.BASE_URL}/getCalibratedSensorReadings'
        
        params = {
            'site_code': sensor.site_code,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'interval': 'hourly'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            readings_to_create = []
            
            # Parse response (structure depends on actual API)
            if 'readings' in data:
                for entry in data['readings']:
                    timestamp_str = entry.get('timestamp')
                    
                    if not timestamp_str:
                        continue
                    
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timezone.is_naive(timestamp):
                            timestamp = timezone.make_aware(timestamp)
                        
                        # Check if exists
                        if Reading.objects.filter(
                            sensor=sensor,
                            timestamp=timestamp
                        ).exists():
                            continue
                        
                        reading = Reading(
                            sensor=sensor,
                            timestamp=timestamp,
                            no2=self._parse_value(entry.get('no2')),
                            pm25=self._parse_value(entry.get('pm2_5')),
                            pm10=self._parse_value(entry.get('pm10')),
                        )
                        readings_to_create.append(reading)
                    
                    except (ValueError, TypeError) as e:
                        continue
            
            # Bulk create
            if readings_to_create:
                Reading.objects.bulk_create(readings_to_create, ignore_conflicts=True)
            
            return len(readings_to_create)
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.WARNING(f'  Error fetching data: {e}')
            )
            return 0
    
    def _parse_value(self, value):
        """Parse and validate pollutant value."""
        if value is None:
            return None
        try:
            decimal_val = Decimal(str(value))
            return decimal_val if decimal_val >= 0 else None
        except (ValueError, TypeError):
            return None