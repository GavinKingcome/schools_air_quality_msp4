"""
Air Quality Models for AirAware London

Hybrid data approach:
1. Direct sensor reading: If urban background sensor within 150m
2. LAEI × adjustment: For all other schools (preserves spatial detail, adds temporal variation)

Data sources:
- LAQN: Reference-grade monitoring stations
- Breathe London: Calibrated low-cost sensors via OpenAQ
- LAEI 2022: Modelled baseline concentrations (20m grid)
"""

from django.db import models
from django.utils import timezone


class Sensor(models.Model):
    """
    Air quality monitoring sensor/station.
    
    Supports both LAQN (reference-grade) and Breathe London (low-cost calibrated)
    sensors with appropriate metadata for each network.
    """
    
    NETWORK_CHOICES = [
        ('LAQN', 'London Air Quality Network'),
        ('BREATHE', 'Breathe London'),
    ]
    
    SITE_TYPE_CHOICES = [
        ('roadside', 'Roadside'),
        ('urban_background', 'Urban Background'),
        ('suburban', 'Suburban'),
        ('industrial', 'Industrial'),
        ('kerbside', 'Kerbside'),
        ('rural', 'Rural'),
    ]
    
    # Identifiers
    site_code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    
    # Location
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Classification
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES, db_index=True)
    site_type = models.CharField(max_length=30, choices=SITE_TYPE_CHOICES, default='urban_background')
    borough = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    date_opened = models.DateField(null=True, blank=True)
    date_closed = models.DateField(null=True, blank=True)
    
    # Network-specific metadata (JSON)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['network', 'name']
        indexes = [
            models.Index(fields=['network', 'is_active']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['site_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.network})"
    
    @property
    def is_reference_grade(self) -> bool:
        """LAQN sensors are reference-grade instruments."""
        return self.network == 'LAQN'
    
    @property
    def is_urban_background(self) -> bool:
        """Check if sensor is urban background type."""
        return self.site_type == 'urban_background'
    
    def get_latest_reading(self):
        """Get most recent reading from this sensor."""
        return self.readings.order_by('-timestamp').first()


class Reading(models.Model):
    """
    Pollution reading from a sensor at a specific time.
    
    Stores hourly averaged values for key pollutants.
    All concentrations in µg/m³.
    """
    
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='readings'
    )
    timestamp = models.DateTimeField(db_index=True)
    
    # Pollutant concentrations (µg/m³)
    no2 = models.FloatField(null=True, blank=True, help_text='NO₂ µg/m³')
    pm25 = models.FloatField(null=True, blank=True, help_text='PM2.5 µg/m³')
    pm10 = models.FloatField(null=True, blank=True, help_text='PM10 µg/m³')
    o3 = models.FloatField(null=True, blank=True, help_text='O₃ µg/m³')
    nox = models.FloatField(null=True, blank=True, help_text='NOx µg/m³')
    
    # Data quality flag
    is_provisional = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['sensor', 'timestamp']
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sensor', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.sensor.site_code} @ {self.timestamp}"


class SensorAnnualStats(models.Model):
    """
    Annual statistics for a sensor, used for calculating adjustment factors.
    
    The adjustment factor = current_reading / annual_mean tells us how
    current conditions compare to typical conditions.
    """
    
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='annual_stats'
    )
    year = models.IntegerField()
    
    # Annual means (µg/m³)
    no2_mean = models.FloatField(null=True, blank=True)
    pm25_mean = models.FloatField(null=True, blank=True)
    pm10_mean = models.FloatField(null=True, blank=True)
    o3_mean = models.FloatField(null=True, blank=True)
    
    # Data capture rate (0-100%)
    capture_rate = models.FloatField(null=True, blank=True)
    
    class Meta:
        unique_together = ['sensor', 'year']
        ordering = ['-year']
    
    def __str__(self):
        return f"{self.sensor.site_code} - {self.year}"
