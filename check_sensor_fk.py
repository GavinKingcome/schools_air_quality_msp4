#!/usr/bin/env python
"""Check actual sensor relationships in database"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from schools.models import School
from air_quality.models import Sensor

print('Schools with ForeignKey sensor relationships:\n')

# Check a few schools
schools = School.objects.filter(data_source='ADJUSTED')[:5]

for school in schools:
    print(f'{school.name}:')
    print(f'  reference_sensor (object): {school.reference_sensor}')
    print(f'  reference_sensor.id: {school.reference_sensor.id if school.reference_sensor else None}')
    print(f'  reference_sensor.site_code: {school.reference_sensor.site_code if school.reference_sensor else None}')
    print(f'  reference_sensor_id (FK): {school.reference_sensor_id}')
    print()
