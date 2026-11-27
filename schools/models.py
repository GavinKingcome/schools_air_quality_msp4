from django.db import models
from django.utils import timezone
from air_quality.models import Sensor
from django.contrib.auth.models import User
# Limits and guidelines for ANNUAL averages (µg/m³).
# Only compare these with an annual figure, never with an hourly reading.
#   UK: Air Quality Standards Regulations 2010 (PM2.5: 20 since 1 January 2020)
#   EU 2024: revised Ambient Air Quality Directive, limit values from 2030
#   WHO: 2021 air quality guidelines
ANNUAL_LIMITS = {
    'no2':  {'uk': 40, 'eu_2024': 20, 'who': 10},
    'pm25': {'uk': 20, 'eu_2024': 10, 'who': 5},
    'pm10': {'uk': 40, 'eu_2024': 20, 'who': 15},
}
# WHO 2021 air quality guidelines for 24-hour averages (µg/m³). Only compare
# these with an average over 24 hours, never with a single hour's reading.
# The WHO says they shouldn't be exceeded on more than 3 or 4 days a year.
DAILY_GUIDELINES = {'no2': 25, 'pm25': 15, 'pm10': 45}


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
        ('all_through', 'All-through School'),
        ('special', 'Special School'),
        ('independent', 'Independent School'),
    ]
    
    # Basic Info
    urn = models.CharField(max_length=20, unique=True, null=True, blank=True)  # Identity: the Department for Education URN from GIAS. Imports match on it.
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=10)
    borough = models.CharField(max_length=100, blank=True)
    lsoa21 = models.CharField(
        max_length=12, blank=True,
        help_text='2021-boundary LSOA code, for IMD/IDACI joins',
    )
    
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
    has_pre_reception_provision = models.BooleanField(
        default=False,
        help_text='Nursery classes, or admits children aged 3 or under',
    )
    
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
    # Latest reading, pollutant by pollutant (see schools/estimates.py)
    # =========================================================================

    def get_current_reading(self, data=None) -> dict:
        """
        The school's latest figures, worked out separately for each pollutant.

        Each pollutant uses the school's own sensor if it has a value from
        the last 48 hours, otherwise the first suitable sensor on the
        school's ranked list. The full detail is in result['pollutants'].

        data: a SensorData from SensorData.load(schools). Pages showing many
        schools load it once and pass it in; without it, this loads the
        data for this one school.

        Until the popup and school page show a sensor per pollutant (step 5),
        the top-level keys describe one sensor only: the one used for the
        first pollutant that has a figure. Pollutants from other sensors are
        listed in 'unadjusted', so the page doesn't credit that sensor with
        them.
        """
        from schools.estimates import POLLUTANTS, SCHOOL_LAEI_FIELDS, SensorData, estimate_school

        if data is None:
            data = SensorData.load([self])
        estimates = estimate_school(self, data)

        result = {
            'timestamp': timezone.now(),
            'source': self.data_source,
            'method': None,
            'confidence': 'low',
            'no2': None,
            'pm25': None,
            'pm10': None,
            'pollutants': estimates,
        }

        shown = next((estimates[p] for p in POLLUTANTS if estimates[p]), None)

        if shown is None:
            # No sensor figure for any pollutant: LAEI 2022 only
            if self._has_laei_data():
                for p in POLLUTANTS:
                    value = getattr(self, SCHOOL_LAEI_FIELDS[p])
                    result[p] = float(value) if value is not None else None
                result.update({
                    'method': 'laei_only',
                    'note': 'Modelled annual average — current conditions may vary',
                })
            return result

        same_sensor = [
            p for p in POLLUTANTS
            if estimates[p] and estimates[p]['sensor_code'] == shown['sensor_code']
        ]
        for p in same_sensor:
            result[p] = estimates[p]['value']

        result.update({
            'method': 'direct' if shown['kind'] == 'measured' else 'laei_adjusted',
            'confidence': shown['confidence'],
            'sensor_code': shown['sensor_code'],
            'sensor_network': shown['sensor_network'],
            'sensor_site_type': shown['sensor_site_type'],
            'sensor_is_reference': shown['sensor_is_reference'],
            'sensor_distance': shown['sensor_distance'],
            'reading_timestamp': shown['reading_timestamp'],
            # Pollutants this sensor didn't supply
            'unadjusted': [p for p in POLLUTANTS if p not in same_sensor],
            # Reading now ÷ this sensor's yearly average, e.g. {'no2': 1.2}
            'compared_with_usual': {
                p: estimates[p]['compared_with_average'] for p in same_sensor
                if estimates[p]['compared_with_average'] is not None
            },
        })
        return result

    def _has_laei_data(self) -> bool:
        """Check if school has LAEI baseline data."""
        return any([self.no2_2022, self.pm25_2022, self.pm10_mean_2022])

    def get_threshold_status(self) -> dict:
        """
        Compare the school's typical year with the UK, EU 2024 and WHO
        annual limits.

        The typical year is the LAEI 2022 annual average at the school.
        These limits are for annual averages, so they are never compared
        with a single hourly reading.
        """
        annual = {
            'no2': self.no2_2022,
            'pm25': self.pm25_2022,
            'pm10': self.pm10_mean_2022,
        }

        status = {}
        for pollutant, value in annual.items():
            if value is None:
                continue
            value = float(value)
            t = ANNUAL_LIMITS[pollutant]
            status[pollutant] = {
                'value': round(value, 1),
                'uk': t['uk'],
                'eu_2024': t['eu_2024'],
                'who': t['who'],
                'meets_uk': value <= t['uk'],
                'meets_eu_2024': value <= t['eu_2024'],
                'meets_who': value <= t['who'],
            }

        return status
    
class SchoolSensor(models.Model):
    """
    One nearby sensor on a school's ranked list (rank 1 = first choice).

    assign_sensors rebuilds every school's list each hour: sensors within
    2 km that have reported in the last 7 days and have a yearly average,
    urban background first, then other site types, nearest first within
    each group. A school's own direct sensor is never on its list.
    When a page opens, each pollutant uses the first sensor on the list
    with a fresh reading and a yearly average for that pollutant.
    """
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='sensor_list',
    )
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='school_lists',
    )
    rank = models.PositiveSmallIntegerField(help_text='1 = first choice')
    distance_m = models.DecimalField(
        max_digits=7,
        decimal_places=1,
        help_text='Distance from the school, in metres',
    )

    class Meta:
        ordering = ['school', 'rank']
        constraints = [
            models.UniqueConstraint(fields=['school', 'sensor'], name='unique_school_sensor'),
            models.UniqueConstraint(fields=['school', 'rank'], name='unique_school_rank'),
        ]

    def __str__(self):
        return f'{self.school.name}: {self.rank}. {self.sensor.site_code} ({self.distance_m} m)'



class SchoolNote(models.Model):
    """
    User-submitted notes about a school's air quality environment.
    
    Allows parents, teachers and administrators to share observations
    such as nearby construction, traffic changes, or ventilation concerns
    that may affect air quality readings.
    """
    
    CATEGORY_CHOICES = [
        ('observation', 'General Observation'),
        ('concern', 'Air Quality Concern'),
        ('improvement', 'Improvement Suggestion'),
        ('update', 'School Environment Update'),
    ]
    
    school = models.ForeignKey(
        'School',
        on_delete=models.CASCADE,
        related_name='notes'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='school_notes'
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField(
        help_text='Share observations about air quality conditions at this school.'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='observation'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'School Note'
        verbose_name_plural = 'School Notes'
    
    def __str__(self):
        return f"{self.title} - {self.school.name}"