from django.shortcuts import render
from .models import School
import json

def schools_list(request):
    """List all schools"""
    schools = School.objects.all().order_by('name')
    return render(request, 'schools/schools_list.html', {'schools': schools})

def login_view(request):
    """Login page placeholder"""
    return render(request, 'schools/login.html')

# Create your views here.
