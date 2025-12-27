from django.db import models

# Create your models here.
class School(models.Model):
    """Model representing a school location"""
    
    # Basic Information
    name = models.CharField(max_length=200, help_text="School name")
    address = models.CharField(max_length=255, help_text="Street address")
    city = models.CharField(max_length=100, default="")
    postcode = models.CharField(max_length=10)
    
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
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
    
    def __str__(self):
        return self.name