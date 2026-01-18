"""
Django management command to fetch annual statistics from LAQN sensors.

These statistics are used to calculate adjustment factors:
    adjustment = sensor_now / sensor_annual_mean

Usage:
    python manage.py fetch_annual_stats
    python manage.py fetch_annual_stats --year=2023
    python manage.py fetch_annual_stats --year=2022 --year=2023
"""

from django.core.management.base import BaseCommand
from air_quality.models import Sensor, SensorAnnualStats
from air_quality.services.laqn_api import LAQNApi
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch annual statistics from LAQN sensors for adjustment factor calculations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            action='append',
            type=int,
            help='Year(s) to fetch (can specify multiple). Defaults to previous year.'
        )
        parser.add_argument(
            '--sensor',
            type=str,
            help='Fetch for specific sensor site_code only'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing annual stats'
        )
    
    def handle(self, *args, **options):
        api = LAQNApi()
        
        # Determine years to fetch
        years = options.get('year') or [datetime.now().year - 1]
        
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
            self.stdout.write(self.style.WARNING('No active LAQN sensors found.'))
            return
        
        self.stdout.write(f'Fetching annual statistics for {sensors.count()} LAQN sensors')
        self.stdout.write(f'Years: {", ".join(map(str, years))}')
        self.stdout.write('')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for sensor in sensors:
            self.stdout.write(f'  {sensor.site_code} ({sensor.name[:30]}):')
            
            for year in years:
                # Check if already exists
                existing = SensorAnnualStats.objects.filter(
                    sensor=sensor,
                    year=year
                ).first()
                
                if existing and not options['overwrite']:
                    self.stdout.write(f'    {year}: Already exists (use --overwrite to update)')
                    skipped_count += 1
                    continue
                
                # Fetch each pollutant
                try:
                    no2_mean = api.get_annual_mean(sensor.site_code, year, 'NO2')
                    pm25_mean = api.get_annual_mean(sensor.site_code, year, 'PM25')
                    pm10_mean = api.get_annual_mean(sensor.site_code, year, 'PM10')
                    o3_mean = api.get_annual_mean(sensor.site_code, year, 'O3')
                    
                    # Check if we got any data
                    if not any([no2_mean, pm25_mean, pm10_mean, o3_mean]):
                        self.stdout.write(
                            self.style.WARNING(f'    {year}: No data available')
                        )
                        skipped_count += 1
                        continue
                    
                    # Create or update
                    stats, created = SensorAnnualStats.objects.update_or_create(
                        sensor=sensor,
                        year=year,
                        defaults={
                            'no2_mean': no2_mean,
                            'pm25_mean': pm25_mean,
                            'pm10_mean': pm10_mean,
                            'o3_mean': o3_mean,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        status = self.style.SUCCESS('Created')
                    else:
                        updated_count += 1
                        status = self.style.SUCCESS('Updated')
                    
                    # Format the values for display
                    values = []
                    if no2_mean:
                        values.append(f'NO₂={no2_mean:.1f}')
                    if pm25_mean:
                        values.append(f'PM2.5={pm25_mean:.1f}')
                    if pm10_mean:
                        values.append(f'PM10={pm10_mean:.1f}')
                    if o3_mean:
                        values.append(f'O₃={o3_mean:.1f}')
                    
                    self.stdout.write(f'    {year}: {status} - {", ".join(values)} µg/m³')
                    
                except Exception as e:
                    logger.error(f'Error fetching stats for {sensor.site_code} {year}: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'    {year}: Error - {str(e)[:50]}')
                    )
                    error_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.SUCCESS('Fetch Complete'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'  Created: {created_count}')
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        self.stdout.write(f'  Errors:  {error_count}')
        
        # Show coverage summary
        total_sensors = Sensor.objects.filter(network='LAQN', is_active=True).count()
        sensors_with_stats = SensorAnnualStats.objects.values('sensor').distinct().count()
        
        self.stdout.write('')
        self.stdout.write(f'LAQN sensors with annual stats: {sensors_with_stats}/{total_sensors}')
