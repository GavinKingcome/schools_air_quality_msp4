from django.contrib import admin
from .models import School

# Register your models here.
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'postcode', 'school_type', 'student_count']
    list_filter = ['school_type', 'city']
    search_fields = ['name', 'address', 'city', 'postcode']
    ordering = ['name']

