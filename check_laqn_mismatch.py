#!/usr/bin/env python
"""Check LAQN site codes in database vs School records"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from air_quality.models import Sensor
from schools.models import School

print('LAQN sensors in database:')
laqn = Sensor.objects.filter(network='LAQN')
for s in laqn:
    reading_count = s.readings.count()
    print(f'  {s.site_code} - {s.name} ({reading_count} readings)')

print('\n\nReference sensors being requested by schools:')
schools_needing_laqn = School.objects.filter(
    data_source='ADJUSTED',
    reference_sensor__isnull=False
).values_list('reference_sensor', flat=True).distinct()

for ref in schools_needing_laqn[:10]:
    count = School.objects.filter(reference_sensor=ref).count()
    print(f'  "{ref}" - {count} schools')
