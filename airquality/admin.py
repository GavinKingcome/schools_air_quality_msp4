from django.contrib import admin
from .models import AirQualityReading

@admin.register(AirQualityReading)
class AirQualityReadingAdmin(admin.ModelAdmin):
    list_display = ['school', 'timestamp', 'pm25', 'pm10', 'no2', 'aqi', 'source']
    list_filter = ['school', 'source', 'timestamp']
    search_fields = ['school__name']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        ('Location & Time', {
            'fields': ('school', 'timestamp')
        }),
        ('Pollutant Measurements', {
            'fields': ('pm25', 'pm10', 'no2', 'o3', 'co', 'so2')
        }),
        ('Air Quality Index', {
            'fields': ('aqi',)
        }),
        ('Metadata', {
            'fields': ('source',)
        }),
    )

# Register your models here.
