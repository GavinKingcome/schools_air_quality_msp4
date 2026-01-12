from django.db import models

# Create your models here.
class School(models.Model):
    """Model representing a school location"""
    
    SCHOOL_TYPE_CHOICES = [
        ('nursery', 'Nursery'),
        ('primary', 'Primary'),
    ]
    
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=10)
    borough = models.CharField(max_length=100, blank=True) 
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    school_type = models.CharField(max_length=10, choices=SCHOOL_TYPE_CHOICES)
    student_count = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Location for mapping (required for map visualization)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Longitude coordinate")
    
    # Additional Info
    school_type = models.CharField(max_length=50, choices=[
        ('nursery', 'Nursery School'),
        ('primary', 'Primary School'),
    ], default='primary')
    
    student_count = models.IntegerField(null=True, blank=True, help_text="Approximate number of students")
    
    # Air Quality Data (from LAEI 2022)
    no2_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="NO₂ concentration µg/m³")
    nox_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="NOₓ concentration µg/m³")
    pm25_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="PM2.5 concentration µg/m³")
    pm10_mean_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="PM10 annual mean µg/m³")
    pm10_days_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="PM10 days exceeding limit")
    laei_data_available = models.BooleanField(default=False, help_text="LAEI pollution data available")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']