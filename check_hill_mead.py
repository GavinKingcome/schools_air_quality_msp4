#!/usr/bin/env python
"""Check specific school configuration"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from schools.models import School

# Find Hill Mead
school = School.objects.get(name='Hill Mead Primary School')

print(f'School: {school.name}')
print(f'Data source: {school.data_source}')
print(f'Direct sensor: {school.direct_sensor}')
print(f'Reference sensor: {school.reference_sensor}')
if school.reference_sensor:
    print(f'  Site code: {school.reference_sensor.site_code}')
    print(f'  Name: {school.reference_sensor.name}')
    print(f'  Distance: {school.reference_sensor_distance}m')
    print(f'  Readings: {school.reference_sensor.readings.count()}')
    latest = school.reference_sensor.get_latest_reading()
    if latest:
        print(f'  Latest reading: {latest.timestamp}')
        print(f'  NO2: {latest.no2}, PM2.5: {latest.pm25}, PM10: {latest.pm10}')

print(f'\nLAEI data available: {school.laei_data_available}')
print(f'  NO2 2022: {school.no2_2022}')
print(f'  PM2.5 2022: {school.pm25_2022}')
print(f'  PM10 2022: {school.pm10_mean_2022}')

print('\n--- Testing get_current_reading() method ---')
try:
    result = school.get_current_reading()
    if result:
        print(f'Method: {result.get("method")}')
        print(f'Data: {result.get("data")}')
    else:
        print('get_current_reading() returned None')
except Exception as e:
    print(f'Error calling get_current_reading(): {e}')
