from django.shortcuts import render
from schools.models import School
from air_quality.models import Sensor
import json

def map_view(request):
    """Display all schools and sensors on a map"""
    schools = School.objects.all()
    sensors = Sensor.objects.filter(is_active=True)
    
    # Prepare school data for JavaScript
    schools_data = []
    for school in schools:
        # Get current reading to determine actual data source
        current_reading = school.get_current_reading()
        method = current_reading.get('method', '')
        
        # Map method to data_source for template
        if method == 'direct':
            data_source = 'DIRECT'
        elif method == 'laei_adjusted':
            data_source = 'ADJUSTED'
        else:  # laei_only or empty
            data_source = 'LAEI_ONLY'
        
        # Get adjustment factor info if available
        adjustment_factors = current_reading.get('adjustment_factors', {})
        reading_timestamp = adjustment_factors.get('reading_timestamp')
        is_school_hours = adjustment_factors.get('is_school_hours', True)
        
        schools_data.append({
            'id': school.id,
            'name': school.name,
            'address': school.address,
            'city': school.city,
            'postcode': school.postcode,
            'borough': school.borough,
            'school_type': school.get_school_type_display(),
            'student_count': school.student_count,
            'latitude': float(school.latitude),
            'longitude': float(school.longitude),
            # LAEI 2022 pollution data
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
            'reading_timestamp': reading_timestamp.isoformat() if reading_timestamp else None,
            'is_school_hours': is_school_hours,
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
    
    context = {
        'schools_json': json.dumps(schools_data),
        'sensors_json': json.dumps(sensors_data),
    }
    
    return render(request, 'maps/map.html', context)

# Create your views here.
