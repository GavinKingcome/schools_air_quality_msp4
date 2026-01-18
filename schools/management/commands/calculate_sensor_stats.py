"""
Calculate annual statistics for sensors (needed for adjustment factors).

Usage:
    python manage.py calculate_sensor_stats
    python manage.py calculate_sensor_stats --year 2024
"""

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from schools.models import Sensor, Reading, SensorAnnualStats


class Command(BaseCommand):
    help = 'Calculate annual statistics for sensors'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Specific year to calculate (defaults to all years with data)'
        )
    
    def handle(self, *args, **options):
        target_year = options.get('year')
        
        sensors = Sensor.objects.filter(is_active=True)
        
        for sensor in sensors:
            # Determine which years to process
            if target_year:
                years = [target_year]
            else:
                # Get all years with readings
                years = Reading.objects.filter(
                    sensor=sensor
                ).dates('timestamp', 'year')
                years = [d.year for d in years]
            
            for year in years:
                self.stdout.write(f'Calculating {sensor.site_code} - {year}...')
                
                # Get readings for this year
                readings = Reading.objects.filter(
                    sensor=sensor,
                    timestamp__year=year
                )
                
                count = readings.count()
                
                if count == 0:
                    self.stdout.write(
                        self.style.WARNING(f'  No data for {year}')
                    )
                    continue
                
                # Calculate capture rate
                total_hours = 365 * 24
                if year % 4 == 0:  # Leap year
                    total_hours = 366 * 24
                
                capture_rate = (count / total_hours) * 100
                
                # Need at least 75% data coverage
                if capture_rate < 75:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  Insufficient data: {capture_rate:.1f}% '
                            f'(minimum 75% required)'
                        )
                    )
                    continue
                
                # Calculate means
                aggregates = readings.aggregate(
                    no2_mean=Avg('no2'),
                    pm25_mean=Avg('pm25'),
                    pm10_mean=Avg('pm10'),
                    o3_mean=Avg('o3'),
                )
                
                # Create or update stats
                stats, created = SensorAnnualStats.objects.update_or_create(
                    sensor=sensor,
                    year=year,
                    defaults={
                        'no2_mean': aggregates['no2_mean'],
                        'pm25_mean': aggregates['pm25_mean'],
                        'pm10_mean': aggregates['pm10_mean'],
                        'o3_mean': aggregates['o3_mean'],
                        'capture_rate': round(capture_rate, 2),
                    }
                )
                
                action = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {action}: {count} readings, '
                        f'{capture_rate:.1f}% coverage'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('\nDone!'))