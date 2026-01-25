from django.db import models
from django.utils import timezone
from air_quality.models import Sensor


class School(models.Model):
    """Model representing a school location with air quality data."""
    
    DATA_SOURCE_CHOICES = [
        ('DIRECT', 'Direct Sensor Reading'),
        ('ADJUSTED', 'LAEI Adjusted by Sensor'),
        ('LAEI', 'LAEI Baseline Only'),
    ]
    
    SCHOOL_TYPE_CHOICES = [
        ('nursery', 'Nursery School'),
        ('primary', 'Primary School'),
    ]
    
    # Basic Info
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=10)
    borough = models.CharField(max_length=100, blank=True)
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    # Location for mapping
    latitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Longitude coordinate")
    
    # School Info
    school_type = models.CharField(max_length=50, choices=SCHOOL_TYPE_CHOICES, default='primary')
    student_count = models.IntegerField(null=True, blank=True, help_text="Approximate number of students")
    
    # =========================================================================
    # LAEI 2022 Baseline Data (your existing fields)
    # =========================================================================
    no2_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, 
                                    help_text="NO₂ concentration µg/m³")
    nox_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, 
                                    help_text="NOₓ concentration µg/m³")
    pm25_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, 
                                     help_text="PM2.5 concentration µg/m³")
    pm10_mean_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, 
                                          help_text="PM10 annual mean µg/m³")
    pm10_days_2022 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, 
                                          help_text="PM10 days exceeding limit")
    laei_data_available = models.BooleanField(default=False, help_text="LAEI pollution data available")
    
    # =========================================================================
    # NEW: Sensor Integration Fields
    # =========================================================================
    data_source = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default='LAEI',
        help_text="Current data methodology"
    )
    
    # Direct sensor: Urban background within 150m (for direct readings - Breathe London)
    direct_sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_schools',
        help_text='Urban background sensor within 150m'
    )
    direct_sensor_distance = models.DecimalField(
        max_digits=7, decimal_places=1,
        null=True, blank=True,
        help_text='Distance to direct sensor in meters'
    )
    
    # Reference sensor: Nearest LAQN for adjustment factors
    reference_sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reference_schools',
        help_text='Nearest LAQN sensor for adjustment factors'
    )
    reference_sensor_distance = models.DecimalField(
        max_digits=8, decimal_places=1,
        null=True, blank=True,
        help_text='Distance to reference sensor in meters'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'School'
        verbose_name_plural = 'Schools'
    
    def __str__(self):
        return self.name
    
    # =========================================================================
    # NEW: Methods for Real-Time Data
    # =========================================================================
    
    def get_current_reading(self) -> dict:
        """
        Get current air quality estimate using hybrid approach.
        
        1. Direct sensor (urban background ≤150m): Use reading directly
        2. LAEI × adjustment: Scale baseline by sensor temporal factor
        3. LAEI only: Fall back to modelled baseline
        """
        result = {
            'timestamp': timezone.now(),
            'source': self.data_source,
            'method': None,
            'confidence': 'low',
            'no2': None,
            'pm25': None,
            'pm10': None,
        }
        
        # Method 1: Direct sensor reading
        if self.direct_sensor:
            reading = self.direct_sensor.get_latest_reading()
            if reading and self._is_reading_fresh(reading):
                result.update({
                    'no2': float(reading.no2) if reading.no2 else None,
                    'pm25': float(reading.pm25) if reading.pm25 else None,
                    'pm10': float(reading.pm10) if reading.pm10 else None,
                    'method': 'direct',
                    'confidence': 'high' if self.direct_sensor.is_reference_grade else 'medium-high',
                    'sensor_code': self.direct_sensor.site_code,
                    'sensor_distance': float(self.direct_sensor_distance) if self.direct_sensor_distance else None,
                })
                return result
        
        # Method 2: LAEI baseline × adjustment factor
        if self.reference_sensor and self._has_laei_data():
            adjustment = self._calculate_adjustment_factor()
            if adjustment:
                result.update({
                    'no2': self._apply_adjustment(self.no2_2022, adjustment.get('no2')),
                    'pm25': self._apply_adjustment(self.pm25_2022, adjustment.get('pm25')),
                    'pm10': self._apply_adjustment(self.pm10_mean_2022, adjustment.get('pm10')),
                    'method': 'laei_adjusted',
                    'confidence': 'medium',
                    'adjustment_factors': adjustment,
                    'reference_sensor': self.reference_sensor.site_code,
                    'reference_distance': float(self.reference_sensor_distance) if self.reference_sensor_distance else None,
                    'laei_baseline': {
                        'no2': float(self.no2_2022) if self.no2_2022 else None,
                        'pm25': float(self.pm25_2022) if self.pm25_2022 else None,
                        'pm10': float(self.pm10_mean_2022) if self.pm10_mean_2022 else None,
                    }
                })
                return result
        
        # Method 3: LAEI baseline only
        if self._has_laei_data():
            result.update({
                'no2': float(self.no2_2022) if self.no2_2022 else None,
                'pm25': float(self.pm25_2022) if self.pm25_2022 else None,
                'pm10': float(self.pm10_mean_2022) if self.pm10_mean_2022 else None,
                'method': 'laei_only',
                'confidence': 'low',
                'note': 'Modelled annual average — current conditions may vary',
            })
        
        return result
    
    def _is_reading_fresh(self, reading, max_age_seconds: int = 86400) -> bool:
        """Check if reading is recent enough (default: 2 hours)."""
        if not reading or not reading.timestamp:
            return False
        age = (timezone.now() - reading.timestamp).total_seconds()
        return age <= max_age_seconds
    
    def _has_laei_data(self) -> bool:
        """Check if school has LAEI baseline data."""
        return any([self.no2_2022, self.pm25_2022, self.pm10_mean_2022])
    
    def _apply_adjustment(self, baseline, factor) -> float:
        """Apply adjustment factor to baseline with safety checks."""
        if baseline is None or factor is None:
            return float(baseline) if baseline else None
        
        baseline_float = float(baseline)
        # Cap extreme adjustments (sensor malfunction protection)
        capped_factor = max(0.2, min(factor, 5.0))
        return round(baseline_float * capped_factor, 1)
    
    def _calculate_adjustment_factor(self) -> dict:
        """
        Calculate adjustment factor using daytime readings only.
        School hours: 7:00 - 18:30
        """
        if not self.reference_sensor:
            return {}
    
        reading = self.reference_sensor.get_latest_reading()
        if not reading or not self._is_reading_fresh(reading):
            return {}
    
        # NEW: Only use daytime readings (7:00-18:30)
        reading_hour = reading.timestamp.hour
        if reading_hour < 7 or reading_hour >= 19:
            return {}  # Skip nighttime readings
    
        stats = self.reference_sensor.annual_stats.order_by('-year').first()
        if not stats:
            return {}
        
        factors = {}
        
        if reading.no2 and stats.no2_mean and float(stats.no2_mean) > 0:
            factors['no2'] = round(float(reading.no2) / float(stats.no2_mean), 3)
        
        if reading.pm25 and stats.pm25_mean and float(stats.pm25_mean) > 0:
            factors['pm25'] = round(float(reading.pm25) / float(stats.pm25_mean), 3)
        
        if reading.pm10 and stats.pm10_mean and float(stats.pm10_mean) > 0:
            factors['pm10'] = round(float(reading.pm10) / float(stats.pm10_mean), 3)
        
        return factors
    
    def get_threshold_status(self) -> dict:
        """Compare current reading against UK, EU 2024, and WHO thresholds."""
        reading = self.get_current_reading()
        
        thresholds = {
            'no2': {'uk': 40, 'eu_2024': 20, 'who': 10},
            'pm25': {'uk': 25, 'eu_2024': 10, 'who': 5},
            'pm10': {'uk': 40, 'eu_2024': 20, 'who': 15},
        }
        
        status = {}
        for pollutant in ['no2', 'pm25', 'pm10']:
            value = reading.get(pollutant)
            if value is None:
                continue
            
            t = thresholds[pollutant]
            status[pollutant] = {
                'value': round(value, 1),
                'meets_uk': value <= t['uk'],
                'meets_eu_2024': value <= t['eu_2024'],
                'meets_who': value <= t['who'],
            }
        
        return status