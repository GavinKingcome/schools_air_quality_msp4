from django.contrib import admin
from .models import School

# Register your models here.
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'borough', 'postcode', 'no2_2022', 'pm25_2022', 'laei_data_available']
    list_filter = ['school_type', 'borough', 'laei_data_available']
    search_fields = ['name', 'address', 'city', 'postcode']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'borough', 'city', 'postcode', 'address')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('School Details', {
            'fields': ('school_type', 'student_count')
        }),
        ('Air Quality Data (LAEI 2022)', {
            'fields': ('laei_data_available', 'no2_2022', 'nox_2022', 'pm25_2022', 'pm10_mean_2022', 'pm10_days_2022')
        }),
    )

