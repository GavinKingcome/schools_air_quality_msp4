#!/usr/bin/env python
"""Check which schools are using LAQN sensor data"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from schools.models import School
from air_quality.models import Sensor

# Schools with direct LAQN sensor readings
direct_laqn = School.objects.filter(
    data_source='DIRECT',
    direct_sensor__isnull=False
)

print(f'Schools with DIRECT LAQN sensor readings: {direct_laqn.count()}')
if direct_laqn.exists():
    print('\nSchools using direct LAQN data:')
    for school in direct_laqn:
        try:
            sensor = Sensor.objects.get(site_code=school.direct_sensor)
            reading_count = sensor.readings.count()
            print(f'\n  {school.name}')
            print(f'    Sensor: {school.direct_sensor} ({sensor.network})')
            print(f'    Readings available: {reading_count}')
        except Sensor.DoesNotExist:
            print(f'\n  {school.name}')
            print(f'    Sensor: {school.direct_sensor} (not found in database)')

# Schools with adjusted data using LAQN reference sensor
adjusted_laqn = School.objects.filter(
    data_source='ADJUSTED',
    reference_sensor__isnull=False
)

print(f'\n\nSchools with ADJUSTED data using LAQN reference sensors: {adjusted_laqn.count()}')
if adjusted_laqn.exists():
    print('\nSample schools using LAQN for adjustment (first 5):')
    for school in adjusted_laqn[:5]:
        try:
            sensor = Sensor.objects.get(site_code=school.reference_sensor)
            reading_count = sensor.readings.count()
            print(f'\n  {school.name}')
            print(f'    Reference sensor: {school.reference_sensor} ({sensor.network})')
            print(f'    Readings available: {reading_count}')
        except Sensor.DoesNotExist:
            print(f'\n  {school.name}')
            print(f'    Reference sensor: {school.reference_sensor} (not found in database)')

# Schools with no sensor data (LAEI only)
laei_only = School.objects.filter(data_source='LAEI')
print(f'\n\nSchools using LAEI modeled data only: {laei_only.count()}')
