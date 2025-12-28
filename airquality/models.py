from django.db import models
from schools.models import School

# Create your models here.
class AirQualityReading(models.Model):
    """Model for air quality measurements"""
    
    # Link to school
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='air_quality_readings')
    
    # Timestamp
    timestamp = models.DateTimeField(db_index=True, help_text="When the measurement was taken")
    
    # Pollutant measurements (in µg/m³ unless noted)
    pm25 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, 
                                help_text="PM2.5 - Fine particulate matter (µg/m³)")
    pm10 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                                help_text="PM10 - Coarse particulate matter (µg/m³)")
    no2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                               help_text="Nitrogen Dioxide (µg/m³)")
    o3 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                              help_text="Ozone (µg/m³)")
    co = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                              help_text="Carbon Monoxide (mg/m³)")
    so2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True,
                               help_text="Sulfur Dioxide (µg/m³)")
    
    # Air Quality Index
    aqi = models.IntegerField(null=True, blank=True, help_text="Air Quality Index (0-500)")
    
    # Data source
    source = models.CharField(max_length=100, blank=True, help_text="Data source (e.g., API, sensor)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Air Quality Reading'
        verbose_name_plural = 'Air Quality Readings'
        indexes = [
            models.Index(fields=['school', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.school.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"