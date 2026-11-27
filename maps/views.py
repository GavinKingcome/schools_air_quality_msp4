from django.shortcuts import render
from schools.models import School, ANNUAL_LIMITS
from schools.estimates import SensorData
from air_quality.models import Sensor
from django.conf import settings
from childcare.models import ChildcareSetting
import json

def as_float(value):
    """Decimal -> float for JavaScript; None stays None."""
    return float(value) if value is not None else None

def estimates_for_js(estimates):
    """Each pollutant's estimate in a form JSON can carry (times as text)."""
    out = {}
    for pollutant, e in estimates.items():
        if e is None:
            out[pollutant] = None
            continue
        out[pollutant] = {
            'value': e['value'],
            'kind': e['kind'],                      # 'measured' or 'estimated'
            'sensor_code': e['sensor_code'],
            'sensor_network': e['sensor_network'],
            'sensor_site_type': e['sensor_site_type'],
            'sensor_distance': e['sensor_distance'],
            'reading_timestamp': e['reading_timestamp'].isoformat(),
            'compared_with_average': e['compared_with_average'],
            'confidence': e['confidence'],
            'day_average': e['day_average'],              # None if too few hours
            'day_hours': e['day_hours'],
            'day_guideline': e['day_guideline'],
            'day_within_guideline': e['day_within_guideline'],
            'method_used': e['method_used'],
            'workings': e['workings'],                    # None for a measurement
        }
    return out


def map_view(request):
    """Display all schools and sensors on a map"""
    schools = list(School.objects.select_related('direct_sensor', 'reference_sensor'))
    sensors = Sensor.objects.filter(is_active=True)
    # Sensor lists, latest readings and yearly averages for every school, in a few queries
    sensor_data = SensorData.load(schools)
    
    # Prepare school data for JavaScript
    schools_data = []
    for school in schools:
        # Get current reading to determine actual data source
        current_reading = school.get_current_reading(sensor_data)
        method = current_reading.get('method', '')
        
        # Map method to data_source for template
        if method == 'direct':
            data_source = 'DIRECT'
        elif method == 'laei_adjusted':
            data_source = 'ADJUSTED'
        else:  # laei_only or empty
            data_source = 'LAEI_ONLY'
        
        # When the reading shown was taken, and whether that was in school hours (7:00 to 19:00)
        reading_timestamp = current_reading.get('reading_timestamp')
        is_school_hours = 7 <= reading_timestamp.hour < 19 if reading_timestamp else True
        
        schools_data.append({
            'id': school.id,
            'name': school.name,
            'address': school.address,
            'city': school.city,
            'postcode': school.postcode,
            'borough': school.borough,
            'school_type': school.get_school_type_display(),
            'has_pre_reception_provision': school.has_pre_reception_provision,
            'student_count': school.student_count,
            'latitude': float(school.latitude),
            'longitude': float(school.longitude),
            # Current/adjusted readings
            'current_no2': current_reading.get('no2'),
            'current_pm25': current_reading.get('pm25'),
            'current_pm10': current_reading.get('pm10'),
            'reading_method': current_reading.get('method'),
            'reading_confidence': current_reading.get('confidence'),
            # LAEI 2022 pollution data (baseline)
            'no2_2022': float(school.no2_2022) if school.no2_2022 else None,
            'nox_2022': float(school.nox_2022) if school.nox_2022 else None,
            'pm25_2022': float(school.pm25_2022) if school.pm25_2022 else None,
            'pm10_mean_2022': float(school.pm10_mean_2022) if school.pm10_mean_2022 else None,
            'pm10_days_2022': float(school.pm10_days_2022) if school.pm10_days_2022 else None,
            'laei_data_available': school.laei_data_available,
            # Dynamic data source based on current sensor availability
            'data_source': data_source,
            'direct_sensor': school.direct_sensor.site_code if school.direct_sensor else None,
            'reference_sensor': school.reference_sensor.site_code if school.reference_sensor else None,
            # The sensor actually used for this reading (direct or adjusted)
            'sensor_code': current_reading.get('sensor_code'),
            'sensor_network': current_reading.get('sensor_network'),
            'sensor_site_type': current_reading.get('sensor_site_type'),
            'sensor_is_reference': current_reading.get('sensor_is_reference'),
            'sensor_distance': current_reading.get('sensor_distance'),
            'unadjusted': current_reading.get('unadjusted', []),
            # Now ÷ the sensor's own annual average, e.g. {'no2': 0.99}; {} if there's no average
            'compared_with_usual': current_reading.get('compared_with_usual', {}),
            'reading_timestamp': reading_timestamp.isoformat() if reading_timestamp else None,
            'is_school_hours': is_school_hours,
            # Each pollutant separately: its own sensor, confidence and reading time
            'pollutants': estimates_for_js(current_reading['pollutants']),
            # Whether the school has any sensor to draw on, for the "no reading" message
            'has_nearby_sensors': bool(school.direct_sensor_id or sensor_data.lists.get(school.id)),
        })
    
    # Prepare sensor data for JavaScript
    sensors_data = []
    for sensor in sensors:
        sensors_data.append({
            'site_code': sensor.site_code,
            'name': sensor.site_code,
            'network': sensor.network,
            'site_type': sensor.site_type,
            'latitude': float(sensor.latitude),
            'longitude': float(sensor.longitude),
            'is_reference_grade': sensor.is_reference_grade,
            'is_urban_background': sensor.is_urban_background,
        })
        
        # Prepare childcare data for JavaScript (mappable providers only)
    childcare_data = [
        {
            'urn': c.urn,
            'name': c.name,
            'provider_type': c.get_provider_type_display(),
            'places': c.places,
            'postcode': c.postcode,
            'borough': c.borough,
            'latitude': c.latitude,
            'longitude': c.longitude,
            'no2_2022': as_float(c.no2_2022),
            'pm25_2022': as_float(c.pm25_2022),
            'pm10_mean_2022': as_float(c.pm10_mean_2022),
        }
        for c in ChildcareSetting.objects.filter(
            latitude__isnull=False, longitude__isnull=False
        ).exclude(provider_type__in=['childminder', 'domestic'])
    ]
    
    context = {
        'schools_json': json.dumps(schools_data),
        'sensors_json': json.dumps(sensors_data),
        'childcare_data': childcare_data,
        'carto_key': settings.CARTO_API_KEY,
        'annual_limits': ANNUAL_LIMITS,
    }
    
    return render(request, 'maps/map.html', context)

# Create your views here.