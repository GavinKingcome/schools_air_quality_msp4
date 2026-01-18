"""
Fetch hourly air quality data from London Air Quality Network (LAQN).

Usage:
    python manage.py fetch_laqn_data
    python manage.py fetch_laqn_data --hours 48  # Get last 48 hours
    python manage.py fetch_laqn_data --site MY1  # Specific site only
"""

import requests
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from schools.models import Sensor, Reading


class Command(BaseCommand):
    help = 'Fetch hourly readings from LAQN sensors'
    
    # LAQN API endpoints (no authentication required)
    BASE_URL = 'https://api.erg.ic.ac.uk/AirQuality'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to fetch (default: 24)'
        )
        parser.add_argument(
            '--site',
            type=str,
            help='Specific site code to fetch (e.g., MY1, CT2)'
        )
    
    def handle(self, *args, **options):
        hours = options['hours']
        site_code = options.get('site')
        
        # Get active LAQN sensors
        sensors = Sensor.objects.filter(network='LAQN', is_active=True)
        if site_code:
            sensors = sensors.filter(site_code=site_code)
        
        if not sensors.exists():
            self.stdout.write(self.style.WARNING('No active LAQN sensors found'))
            return
        
        end_date = timezone.now()
        start_date = end_date - timedelta(hours=hours)
        
        self.stdout.write(f'Fetching data from {start_date} to {end_date}...')
        
        total_created = 0
        
        for sensor in sensors:
            self.stdout.write(f'Processing {sensor.site_code} - {sensor.name}...')
            
            # Fetch data for each pollutant
            readings_data = {}
            
            for species in ['NO2', 'PM25', 'PM10', 'O3', 'NOx']:
                data = self._fetch_species_data(
                    sensor.site_code,
                    species,
                    start_date,
                    end_date
                )
                if data:
                    readings_data[species.lower()] = data
            
            # Combine readings by timestamp
            created = self._save_readings(sensor, readings_data)
            total_created += created
            
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ {created} readings imported')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal: {total_created} readings imported')
        )
    
    def _fetch_species_data(self, site_code, species, start_date, end_date):
        """Fetch hourly data for one pollutant from LAQN API."""
        
        # Format dates for API
        start_str = start_date.strftime('%d-%b-%Y')
        end_str = end_date.strftime('%d-%b-%Y')
        
        # LAQN API endpoint structure
        url = (
            f'{self.BASE_URL}/Data/SiteSpecies/SiteCode={site_code}/'
            f'SpeciesCode={species}/StartDate={start_str}/EndDate={end_str}/Json'
        )
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract readings
            if 'RawAQData' in data and 'Data' in data['RawAQData']:
                readings = {}
                for entry in data['RawAQData']['Data']:
                    timestamp_str = entry.get('@MeasurementDateGMT')
                    value = entry.get('@Value')
                    
                    if timestamp_str and value:
                        try:
                            # Parse timestamp
                            timestamp = datetime.strptime(
                                timestamp_str,
                                '%Y-%m-%d %H:%M:%S'
                            )
                            timestamp = timezone.make_aware(
                                timestamp,
                                timezone.utc
                            )
                            
                            # Convert value
                            value_decimal = Decimal(str(value))
                            if value_decimal >= 0:  # Filter negatives (errors)
                                readings[timestamp] = value_decimal
                        except (ValueError, TypeError) as e:
                            continue
                
                return readings
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.WARNING(f'  Error fetching {species}: {e}')
            )
        
        return {}
    
    def _save_readings(self, sensor, readings_data):
        """Save combined readings to database."""
        
        # Get all unique timestamps
        all_timestamps = set()
        for species_readings in readings_data.values():
            all_timestamps.update(species_readings.keys())
        
        readings_to_create = []
        
        for timestamp in sorted(all_timestamps):
            # Check if reading already exists
            if Reading.objects.filter(
                sensor=sensor,
                timestamp=timestamp
            ).exists():
                continue
            
            # Combine all pollutants for this timestamp
            reading = Reading(
                sensor=sensor,
                timestamp=timestamp,
                no2=readings_data.get('no2', {}).get(timestamp),
                pm25=readings_data.get('pm25', {}).get(timestamp),
                pm10=readings_data.get('pm10', {}).get(timestamp),
                o3=readings_data.get('o3', {}).get(timestamp),
                nox=readings_data.get('nox', {}).get(timestamp),
            )
            readings_to_create.append(reading)
        
        # Bulk create
        if readings_to_create:
            Reading.objects.bulk_create(readings_to_create, ignore_conflicts=True)
        
        return len(readings_to_create)