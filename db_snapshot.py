import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schools_air_quality_msp4.settings')
django.setup()

from schools.models import School
from air_quality.models import Sensor, Reading, SensorAnnualStats
from django.db.models import Count, Max, Min

print('=' * 60)
print('DATABASE SNAPSHOT - CHECKING NETWORKS')
print('=' * 60)

# Check all unique network names
print('\nAll network names in database:')
networks = Sensor.objects.values_list('network', flat=True).distinct()
for network in networks:
    count = Sensor.objects.filter(network=network).count()
    readings = Reading.objects.filter(sensor__network=network).count()
    print(f'  "{network}": {count} sensors, {readings} readings')

print('\n' + '=' * 60)
print('DETAILED SNAPSHOT')
print('=' * 60)

# Schools
total_schools = School.objects.count()
print(f'\nSCHOOLS: {total_schools} total')
print(f'  By Data Source:')
print(f'    DIRECT: {School.objects.filter(data_source="DIRECT").count()}')
print(f'    ADJUSTED: {School.objects.filter(data_source="ADJUSTED").count()}')
print(f'    LAEI_ONLY: {School.objects.filter(data_source="LAEI_ONLY").count()}')
print(f'  By Borough:')
print(f'    Southwark: {School.objects.filter(borough="Southwark").count()}')
print(f'    Lambeth: {School.objects.filter(borough="Lambeth").count()}')

# Sensors
print(f'\nSENSORS: {Sensor.objects.count()} total')
print(f'  By Network:')
print(f'    LAQN: {Sensor.objects.filter(network="LAQN").count()}')
print(f'    BREATHE: {Sensor.objects.filter(network="BREATHE").count()}')
print(f'  Active: {Sensor.objects.filter(is_active=True).count()}')

# LAQN sensors with readings
laqn_with_data = Sensor.objects.filter(network='LAQN').annotate(
    reading_count=Count('readings')
).filter(reading_count__gt=0).order_by('site_code')

print(f'\nLAQN SENSORS WITH DATA: {laqn_with_data.count()} of 16')
for sensor in laqn_with_data:
    latest = Reading.objects.filter(sensor=sensor).order_by('-timestamp').first()
    print(f'  {sensor.site_code} ({sensor.name}): {sensor.readings.count()} readings')
    print(f'    Latest: {latest.timestamp}')

# Readings
total_readings = Reading.objects.count()
print(f'\nREADINGS: {total_readings} total')
laqn_readings = Reading.objects.filter(sensor__network='LAQN').count()
bl_readings = Reading.objects.filter(sensor__network='BREATHE').count()
print(f'  LAQN: {laqn_readings}')
print(f'  BREATHE: {bl_readings}')

if Reading.objects.exists():
    date_range = Reading.objects.aggregate(
        oldest=Min('timestamp'),
        newest=Max('timestamp')
    )
    print(f'  Date range: {date_range["oldest"]} to {date_range["newest"]}')

# Annual Stats
stats = SensorAnnualStats.objects.count()
print(f'\nSENSOR ANNUAL STATS: {stats} records')
if stats > 0:
    years = list(SensorAnnualStats.objects.values_list('year', flat=True).distinct().order_by('year'))
    print(f'  Years covered: {years}')
    print(f'  By Network:')
    for network in ['LAQN', 'BREATHE']:
        count = SensorAnnualStats.objects.filter(sensor__network=network).count()
        sensors = SensorAnnualStats.objects.filter(sensor__network=network).values('sensor').distinct().count()
        print(f'    {network}: {count} records across {sensors} sensors')

# Sample schools
print(f'\nSAMPLE SCHOOLS (first 5):')
for school in School.objects.all()[:5]:
    print(f'  {school.name} ({school.borough})')
    print(f'    Data source: {school.data_source}')
    if school.direct_sensor:
        print(f'    Direct sensor: {school.direct_sensor.site_code}')
    if school.reference_sensor:
        print(f'    Reference sensor: {school.reference_sensor.site_code}')

print('\n' + '=' * 60)
