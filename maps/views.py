from django.shortcuts import render
from schools.models import School
from air_quality.models import Sensor
import json
# from subscriptions.decorators import subscription_required

# @subscription_required  # Temporarily disabled for demo
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
        
        # Get timestamp - for DIRECT it's at top level, for ADJUSTED it's in adjustment_factors
        reading_timestamp = current_reading.get('reading_timestamp')
        if not reading_timestamp:
            adjustment_factors = current_reading.get('adjustment_factors', {})
            reading_timestamp = adjustment_factors.get('reading_timestamp')
            is_school_hours = adjustment_factors.get('is_school_hours', True)
        else:
            # For DIRECT readings, check school hours
            is_school_hours = True  # Direct sensor readings don't have this check yet
            if reading_timestamp:
                reading_hour = reading_timestamp.hour
                is_school_hours = 7 <= reading_hour < 19
        
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
