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
        })
    
    context = {
        'schools_json': json.dumps(schools_data)
    }
    
    return render(request, 'maps/map.html', context)

# Create your views here.
