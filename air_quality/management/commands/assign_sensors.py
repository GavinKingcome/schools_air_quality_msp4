"""
Django management command to assign sensors to schools using hybrid approach.

Methodology:
1. Direct sensor: Urban background sensor within 150m → direct readings
2. Reference sensor: Nearest LAQN (any type) for adjustment factors
3. LAEI only: Schools without reference sensor coverage

The hybrid approach:
- Preserves LAEI's 20m spatial resolution (street-level variation)
- Adds temporal variation from nearest reference sensor
- Only uses direct readings when sensor is genuinely local (≤150m) AND
  is urban background type (not influenced by immediate roadside emissions)

Usage:
    python manage.py assign_sensors
    python manage.py assign_sensors --direct-threshold=150 --reference-threshold=2000
"""

from django.core.management.base import BaseCommand
from air_quality.models import Sensor, School
from math import radians, sin, cos, sqrt, atan2
import logging

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points in meters.
    """
    R = 6371000  # Earth's radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


class Command(BaseCommand):
    help = 'Assign sensors to schools using hybrid approach'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--direct-threshold',
            type=int,
            default=150,
            help='Maximum distance (m) for direct sensor assignment (default: 150)'
        )
        parser.add_argument(
            '--reference-threshold',
            type=int,
            default=2000,
            help='Maximum distance (m) for reference sensor (default: 2000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without saving'
        )
    
    def handle(self, *args, **options):
        direct_threshold = options['direct_threshold']
        reference_threshold = options['reference_threshold']
        dry_run = options['dry_run']
        
        schools = School.objects.all()
        all_sensors = Sensor.objects.filter(is_active=True)
        laqn_sensors = all_sensors.filter(network='LAQN')
        
        self.stdout.write(f'\nHybrid Sensor Assignment')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Schools to process: {schools.count()}')
        self.stdout.write(f'Available sensors: {all_sensors.count()} total, {laqn_sensors.count()} LAQN')
        self.stdout.write(f'Direct threshold: {direct_threshold}m (urban background only)')
        self.stdout.write(f'Reference threshold: {reference_threshold}m (LAQN only)')
        if dry_run:
            self.stdout.write(self.style.WARNING('\n** DRY RUN - no changes will be saved **\n'))
        
        stats = {
            'direct': 0,
            'adjusted': 0,
            'laei_only': 0,
            'direct_laqn': 0,
            'direct_breathe': 0,
        }
        
        for school in schools:
            if not school.latitude or not school.longitude:
                logger.warning(f'School {school.name} has no coordinates')
                continue
            
            # Calculate distances to all sensors
            sensor_distances = []
            for sensor in all_sensors:
                distance = haversine_distance(
                    school.latitude, school.longitude,
                    sensor.latitude, sensor.longitude
                )
                sensor_distances.append({
                    'sensor': sensor,
                    'distance': distance,
                })
            
            # Sort by distance
            sensor_distances.sort(key=lambda x: x['distance'])
            
            # === DIRECT SENSOR ASSIGNMENT ===
            # Only urban background sensors within 150m qualify
            direct_sensor = None
            direct_distance = None
            
            for sd in sensor_distances:
                sensor = sd['sensor']
                distance = sd['distance']
                
                if distance > direct_threshold:
                    break  # No point checking further
                
                if sensor.site_type == 'urban_background':
                    direct_sensor = sensor
                    direct_distance = round(distance, 1)
                    
                    if sensor.network == 'LAQN':
                        stats['direct_laqn'] += 1
                    else:
                        stats['direct_breathe'] += 1
                    break
            
            # === REFERENCE SENSOR ASSIGNMENT ===
            # Nearest LAQN sensor for adjustment factors (any site type)
            reference_sensor = None
            reference_distance = None
            
            laqn_distances = [sd for sd in sensor_distances if sd['sensor'].network == 'LAQN']
            if laqn_distances and laqn_distances[0]['distance'] <= reference_threshold:
                reference_sensor = laqn_distances[0]['sensor']
                reference_distance = round(laqn_distances[0]['distance'], 1)
            
            # === DETERMINE DATA SOURCE ===
            if direct_sensor:
                data_source = 'DIRECT'
                stats['direct'] += 1
            elif reference_sensor:
                data_source = 'ADJUSTED'
                stats['adjusted'] += 1
            else:
                data_source = 'LAEI'
                stats['laei_only'] += 1
            
            # === UPDATE SCHOOL ===
            if not dry_run:
                school.direct_sensor = direct_sensor
                school.direct_sensor_distance = direct_distance
                school.reference_sensor = reference_sensor
                school.reference_sensor_distance = reference_distance
                school.data_source = data_source
                school.save()
            
            # Verbose output for direct assignments (they're rare and interesting)
            if direct_sensor:
                self.stdout.write(
                    f'  ✓ DIRECT: {school.name[:40]:<40} ← '
                    f'{direct_sensor.site_code} ({direct_distance}m, {direct_sensor.network})'
                )
        
        # === SUMMARY ===
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Assignment Summary'))
        self.stdout.write('=' * 50)
        
        total = schools.count()
        
        self.stdout.write(f'\nData source breakdown:')
        self.stdout.write(
            f'  DIRECT (sensor ≤{direct_threshold}m, urban background): '
            f'{stats["direct"]:3d} ({100*stats["direct"]/total:.1f}%)'
        )
        self.stdout.write(
            f'    - LAQN:           {stats["direct_laqn"]:3d}'
        )
        self.stdout.write(
            f'    - Breathe London: {stats["direct_breathe"]:3d}'
        )
        self.stdout.write(
            f'  ADJUSTED (LAEI × sensor factor):                '
            f'{stats["adjusted"]:3d} ({100*stats["adjusted"]/total:.1f}%)'
        )
        self.stdout.write(
            f'  LAEI ONLY (no nearby reference):                '
            f'{stats["laei_only"]:3d} ({100*stats["laei_only"]/total:.1f}%)'
        )
        
        real_time = stats['direct'] + stats['adjusted']
        self.stdout.write(f'\nSchools with real-time capability: {real_time} ({100*real_time/total:.1f}%)')
        
        self.stdout.write('\n' + '-' * 50)
        self.stdout.write('Methodology:')
        self.stdout.write(f'  • DIRECT: Sensor reading used as-is (genuinely local)')
        self.stdout.write(f'  • ADJUSTED: LAEI baseline × (sensor_now / sensor_annual_mean)')
        self.stdout.write(f'  • LAEI ONLY: Modelled 2022 annual average')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n** DRY RUN - no changes saved **'))
