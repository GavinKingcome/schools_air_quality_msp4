#!/usr/bin/env python
"""Check which schools are assigned to working LAQN sensors"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from schools.models import School
from air_quality.models import Sensor

# The 3 LAQN sensors with data
working_sensors = ['LB4', 'LB6', 'SK5']

print('Schools assigned to working LAQN sensors (with real-time data):\n')
print('=' * 70)

for site_code in working_sensors:
    try:
        sensor = Sensor.objects.get(site_code=site_code)
        reading_count = sensor.readings.count()
        latest = sensor.get_latest_reading()
        
        print(f'\n{site_code} - {sensor.name}')
        print(f'  Readings: {reading_count}, Latest: {latest.timestamp if latest else "None"}')
        
        # Schools using this as reference sensor (ADJUSTED)
        ref_schools = School.objects.filter(
            data_source='ADJUSTED',
            reference_sensor=sensor
        ).order_by('name')
        
        # Schools using this as direct sensor (DIRECT)
        direct_schools = School.objects.filter(
            data_source='DIRECT',
            direct_sensor=sensor
        ).order_by('name')
        
        print(f'\n  Schools with ADJUSTED data (using {site_code} for adjustment): {ref_schools.count()}')
        if ref_schools.exists():
            for school in ref_schools:
                dist = f"{school.reference_sensor_distance}m" if school.reference_sensor_distance else "?"
                print(f'    • {school.name} ({dist})')
        
        print(f'\n  Schools with DIRECT data (sensor within 150m): {direct_schools.count()}')
        if direct_schools.exists():
            for school in direct_schools:
                dist = f"{school.direct_sensor_distance}m" if school.direct_sensor_distance else "?"
                print(f'    • {school.name} ({dist})')
        
        print('-' * 70)
        
    except Sensor.DoesNotExist:
        print(f'\n{site_code}: NOT FOUND IN DATABASE')
        print('-' * 70)

# Summary
total_adjusted = School.objects.filter(
    data_source='ADJUSTED',
    reference_sensor__site_code__in=working_sensors
).count()

total_direct = School.objects.filter(
    data_source='DIRECT',
    direct_sensor__site_code__in=working_sensors
).count()

print(f'\n{"=" * 70}')
print(f'SUMMARY: {total_adjusted + total_direct} schools have real-time LAQN data')
print(f'  • {total_adjusted} schools with ADJUSTED readings')
print(f'  • {total_direct} schools with DIRECT readings')
print(f'{"=" * 70}\n')

# Check schools without working sensors
all_adjusted = School.objects.filter(data_source='ADJUSTED')
without_data = all_adjusted.exclude(reference_sensor__site_code__in=working_sensors).count()
print(f'Note: {without_data} schools are configured for ADJUSTED but their')
print(f'      reference sensors don\'t have data yet (13 LAQN sensors missing data)')
