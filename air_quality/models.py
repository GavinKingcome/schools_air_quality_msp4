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


class School(models.Model):
    """
    School with air quality data using hybrid approach.
    
    Data methodology:
    1. If direct_sensor assigned (urban background within 150m):
       → Use direct sensor reading
    2. Otherwise:
       → Use LAEI baseline × adjustment factor from reference sensor
       → This preserves LAEI's 20m spatial detail while adding temporal variation
    """
    
    DATA_SOURCE_CHOICES = [
        ('DIRECT', 'Direct Sensor Reading'),
        ('ADJUSTED', 'LAEI Adjusted by Sensor'),
        ('LAEI', 'LAEI Baseline Only'),
    ]
    
    PHASE_CHOICES = [
        ('nursery', 'Nursery'),
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('all_through', 'All Through'),
    ]
    
    # Identifiers
    urn = models.CharField(max_length=20, unique=True, db_index=True, help_text='Unique Reference Number')
    name = models.CharField(max_length=300)
    
    # Location (WGS84)
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Location (British National Grid) - for LAEI lookups
    easting = models.IntegerField(null=True, blank=True)
    northing = models.IntegerField(null=True, blank=True)
    
    # Address
    address = models.TextField(blank=True)
    postcode = models.CharField(max_length=10, blank=True)
    borough = models.CharField(max_length=100, blank=True)
    
    # School info
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, blank=True)
    establishment_type = models.CharField(max_length=100, blank=True)
    
    # LAEI baseline concentrations (2022 modelled annual means, µg/m³)
    # These capture spatial variation at 20m resolution
    laei_no2 = models.FloatField(null=True, blank=True)
    laei_pm25 = models.FloatField(null=True, blank=True)
    laei_pm10 = models.FloatField(null=True, blank=True)
    laei_nox = models.FloatField(null=True, blank=True)
    
    # Data source indicator
    data_source = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default='LAEI'
    )
    
    # Direct sensor: Only assigned if urban background sensor within 150m
    # Used for direct readings (sensor literally measuring this school's air)
    direct_sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_schools',
        help_text='Urban background sensor within 150m for direct readings'
    )
    direct_sensor_distance = models.FloatField(
        null=True,
        blank=True,
        help_text='Distance to direct sensor in meters'
    )
    
    # Reference sensor: Nearest LAQN sensor for calculating adjustment factors
    # Used when no direct sensor available
    reference_sensor = models.ForeignKey(
        Sensor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reference_schools',
        help_text='Nearest LAQN sensor for temporal adjustment factors'
    )
    reference_sensor_distance = models.FloatField(
        null=True,
        blank=True,
        help_text='Distance to reference sensor in meters'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['borough']),
            models.Index(fields=['data_source']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_current_reading(self) -> dict:
        """
        Get current air quality estimate for this school.
        
        Hybrid approach:
        1. Direct sensor (if urban background within 150m): Use reading directly
        2. LAEI × adjustment: Apply temporal scaling from reference sensor
        3. LAEI only: Fall back to modelled baseline
        
        Returns dict with pollutant values, source methodology, and confidence.
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
        
        # Method 1: Direct sensor reading (urban background within 150m)
        if self.direct_sensor:
            reading = self.direct_sensor.get_latest_reading()
            if reading and self._is_reading_fresh(reading):
                result.update({
                    'no2': reading.no2,
                    'pm25': reading.pm25,
                    'pm10': reading.pm10,
                    'method': 'direct',
                    'confidence': 'high' if self.direct_sensor.is_reference_grade else 'medium-high',
                    'sensor_code': self.direct_sensor.site_code,
                    'sensor_distance': self.direct_sensor_distance,
                })
                return result
        
        # Method 2: LAEI baseline × adjustment factor
        if self.reference_sensor and self._has_laei_data():
            adjustment = self._calculate_adjustment_factor()
            if adjustment:
                result.update({
                    'no2': self._apply_adjustment(self.laei_no2, adjustment.get('no2')),
                    'pm25': self._apply_adjustment(self.laei_pm25, adjustment.get('pm25')),
                    'pm10': self._apply_adjustment(self.laei_pm10, adjustment.get('pm10')),
                    'method': 'laei_adjusted',
                    'confidence': 'medium',
                    'adjustment_factors': adjustment,
                    'reference_sensor': self.reference_sensor.site_code,
                    'reference_distance': self.reference_sensor_distance,
                    'laei_baseline': {
                        'no2': self.laei_no2,
                        'pm25': self.laei_pm25,
                        'pm10': self.laei_pm10,
                    }
                })
                return result
        
        # Method 3: LAEI baseline only (no temporal adjustment available)
        if self._has_laei_data():
            result.update({
                'no2': self.laei_no2,
                'pm25': self.laei_pm25,
                'pm10': self.laei_pm10,
                'method': 'laei_only',
                'confidence': 'low',
                'note': 'Modelled annual average — current conditions may vary',
            })
        
        return result
    
    def _is_reading_fresh(self, reading, max_age_seconds: int = 7200) -> bool:
        """Check if reading is recent enough (default: 2 hours)."""
        if not reading or not reading.timestamp:
            return False
        age = (timezone.now() - reading.timestamp).total_seconds()
        return age <= max_age_seconds
    
    def _has_laei_data(self) -> bool:
        """Check if school has LAEI baseline data."""
        return any([self.laei_no2, self.laei_pm25, self.laei_pm10])
    
    def _apply_adjustment(self, baseline: float, factor: float) -> float:
        """Apply adjustment factor to baseline, with safety checks."""
        if baseline is None or factor is None:
            return baseline
        
        # Cap extreme adjustments (e.g., sensor malfunction)
        capped_factor = max(0.2, min(factor, 5.0))
        return round(baseline * capped_factor, 1)
    
    def _calculate_adjustment_factor(self) -> dict:
        """
        Calculate how current sensor readings compare to annual baseline.
        
        Formula: adjustment = sensor_now / sensor_annual_mean
        
        Example: If sensor reads 40 µg/m³ and annual mean is 32 µg/m³,
        adjustment = 1.25, meaning conditions are 25% above typical.
        
        Returns dict of factors per pollutant, e.g., {'no2': 1.25, 'pm25': 0.92}
        """
        if not self.reference_sensor:
            return {}
        
        # Get latest reading from reference sensor
        reading = self.reference_sensor.get_latest_reading()
        if not reading or not self._is_reading_fresh(reading):
            return {}
        
        # Get annual stats for comparison (most recent year)
        stats = self.reference_sensor.annual_stats.order_by('-year').first()
        if not stats:
            return {}
        
        factors = {}
        
        # Calculate factor for each pollutant
        if reading.no2 and stats.no2_mean and stats.no2_mean > 0:
            factors['no2'] = round(reading.no2 / stats.no2_mean, 3)
        
        if reading.pm25 and stats.pm25_mean and stats.pm25_mean > 0:
            factors['pm25'] = round(reading.pm25 / stats.pm25_mean, 3)
        
        if reading.pm10 and stats.pm10_mean and stats.pm10_mean > 0:
            factors['pm10'] = round(reading.pm10 / stats.pm10_mean, 3)
        
        return factors
    
    def get_threshold_status(self) -> dict:
        """
        Compare current reading against regulatory thresholds.
        
        Returns status for UK, EU 2030, and WHO guidelines.
        """
        reading = self.get_current_reading()
        
        thresholds = {
            'no2': {'uk': 40, 'eu_2030': 20, 'who': 10},
            'pm25': {'uk': 20, 'eu_2030': 10, 'who': 5},
            'pm10': {'uk': 40, 'eu_2030': 20, 'who': 15},
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
                'meets_eu_2030': value <= t['eu_2030'],
                'meets_who': value <= t['who'],
                'category': self._get_category(value, t),
            }
        
        return status
    
    def _get_category(self, value: float, thresholds: dict) -> str:
        """Categorise reading against thresholds."""
        if value <= thresholds['who']:
            return 'meets_who'
        elif value <= thresholds['eu_2030']:
            return 'meets_eu_2030'
        elif value <= thresholds['uk']:
            return 'meets_uk_only'
        else:
            return 'exceeds_uk'
