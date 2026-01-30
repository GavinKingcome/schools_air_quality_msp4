from django.contrib import admin
from .models import Sensor, Reading, SensorAnnualStats


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('site_code', 'name', 'network', 'site_type', 'borough', 'is_active')
    list_filter = ('network', 'site_type', 'is_active', 'borough')
    search_fields = ('site_code', 'name', 'borough')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Identification', {
            'fields': ('site_code', 'name')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'borough')
        }),
        ('Classification', {
            'fields': ('network', 'site_type', 'is_active')
        }),
        ('Dates', {
            'fields': ('date_opened', 'date_closed')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'timestamp', 'no2', 'pm25', 'pm10', 'is_provisional')
    list_filter = ('sensor__network', 'is_provisional', 'timestamp')
    search_fields = ('sensor__site_code', 'sensor__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'
    fieldsets = (
        ('Source', {
            'fields': ('sensor', 'timestamp')
        }),
        ('Pollutant Levels (µg/m³)', {
            'fields': ('no2', 'nox', 'pm25', 'pm10', 'o3')
        }),
        ('Quality', {
            'fields': ('is_provisional',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SensorAnnualStats)
class SensorAnnualStatsAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'year', 'no2_mean', 'pm25_mean', 'pm10_mean', 'capture_rate')
    list_filter = ('year', 'sensor__network')
    search_fields = ('sensor__site_code', 'sensor__name')
    fieldsets = (
        ('Period', {
            'fields': ('sensor', 'year')
        }),
        ('Annual Averages (µg/m³)', {
            'fields': ('no2_mean', 'pm25_mean', 'pm10_mean', 'o3_mean')
        }),
        ('Data Quality', {
            'fields': ('capture_rate',)
        }),
    )
