from django.shortcuts import render
from schools.models import School
import json

def map_view(request):
    """Display all schools on a map"""
    schools = School.objects.all()
    
    # Prepare school data for JavaScript
    schools_data = []
    for school in schools:
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
        })
    
    context = {
        'schools_json': json.dumps(schools_data)
    }
    
    return render(request, 'maps/map.html', context)

# Create your views here.
