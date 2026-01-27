#!/usr/bin/env python
"""Check LAQN sensor data in database"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from air_quality.models import Sensor, Reading
from django.db.models import Count

# Check LAQN sensors
laqn_count = Sensor.objects.filter(network='LAQN').count()
print(f'Total LAQN sensors: {laqn_count}')

# Check if any have readings
laqn_with_readings = Sensor.objects.filter(network='LAQN').annotate(
    reading_count=Count('readings')
).filter(reading_count__gt=0)
print(f'LAQN sensors with readings: {laqn_with_readings.count()}')

# Show sample
if laqn_with_readings.exists():
    print('\nSample sensors with data:')
    for sensor in laqn_with_readings[:5]:
        latest = sensor.get_latest_reading()
        count = sensor.readings.count()
        print(f'\n  {sensor.site_code} ({sensor.name}):')
        print(f'    Total readings: {count}')
        if latest:
            print(f'    Latest timestamp: {latest.timestamp}')
            print(f'    NO2: {latest.no2}, PM2.5: {latest.pm25}, PM10: {latest.pm10}')
else:
    print('\n❌ No LAQN sensors have readings yet.')

# Total readings
total_readings = Reading.objects.filter(sensor__network='LAQN').count()
print(f'\nTotal LAQN readings in database: {total_readings}')

# Check Breathe London too
breathe_count = Sensor.objects.filter(network='BREATHE').count()
breathe_readings = Reading.objects.filter(sensor__network='BREATHE').count()
print(f'\nBreath London sensors: {breathe_count}')
print(f'Breathe London readings: {breathe_readings}')
