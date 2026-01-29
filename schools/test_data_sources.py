from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from schools.models import School
from air_quality.models import Sensor, Reading, SensorAnnualStats


class SchoolDataSourceTest(TestCase):
    """Test cases for School data source selection and adjustment factors"""
    
    def setUp(self):
        """Create test school, sensors, and readings"""
        # Create LAQN sensor with annual stats
        self.laqn_sensor = Sensor.objects.create(
            name="Test LAQN Sensor",
            site_code="LB99",
            network="LAQN",
            latitude=Decimal("51.5100"),
            longitude=Decimal("-0.1300"),
            is_active=True
        )
        
        # Create annual stats for adjustment factors
        SensorAnnualStats.objects.create(
            sensor=self.laqn_sensor,
            year=2024,
            no2_mean=Decimal("40.0"),
            pm25_mean=Decimal("10.0"),
            pm10_mean=Decimal("20.0")
        )
        
        # Create recent reading (within 24 hours)
        Reading.objects.create(
            sensor=self.laqn_sensor,
            timestamp=timezone.now() - timedelta(hours=2),
            no2=Decimal("48.0"),  # 20% higher than annual mean
            pm25=Decimal("12.0"),  # 20% higher
            pm10=Decimal("24.0")   # 20% higher
        )
        
        # Create BREATHE sensor for direct readings
        self.breathe_sensor = Sensor.objects.create(
            name="Test BREATHE Sensor",
            site_code="BL9999",
            network="BREATHE",
            latitude=Decimal("51.5075"),
            longitude=Decimal("-0.1279"),
            is_active=True
        )
        
        Reading.objects.create(
            sensor=self.breathe_sensor,
            timestamp=timezone.now() - timedelta(minutes=30),
            no2=Decimal("25.0"),
            pm25=Decimal("8.5"),
            pm10=Decimal("15.0")
        )
        
        # Create school with LAEI baseline
        self.school = School.objects.create(
            name="Test School with Sensors",
            address="789 Test Road",
            city="London",
            postcode="SE3 3CC",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            borough="Lambeth",
            school_type="primary",
            no2_2022=Decimal("30.0"),
            pm25_2022=Decimal("10.0"),
            pm10_mean_2022=Decimal("18.0"),
            laei_data_available=True,
            data_source='ADJUSTED',
            reference_sensor=self.laqn_sensor,
            reference_sensor_distance=Decimal("500.0")
        )
    
    def test_laei_only_fallback(self):
        """Test that LAEI baseline is returned when no sensors assigned"""
        school = School.objects.create(
            name="LAEI Only School",
            address="999 No Sensor St",
            city="London",
            postcode="SE9 9ZZ",
            latitude=Decimal("51.5000"),
            longitude=Decimal("-0.1000"),
            no2_2022=Decimal("28.5"),
            pm25_2022=Decimal("9.2"),
            pm10_mean_2022=Decimal("16.5"),
            laei_data_available=True,
            data_source='LAEI'
        )
        
        result = school.get_current_reading()
        self.assertEqual(result['method'], 'laei_only')
        self.assertEqual(result['no2'], Decimal("28.5"))
        self.assertEqual(result['pm25'], Decimal("9.2"))
        self.assertEqual(result['pm10'], Decimal("16.5"))
    
    def test_direct_reading(self):
        """Test direct sensor reading when sensor is very close"""
        self.school.data_source = 'DIRECT'
        self.school.direct_sensor = self.breathe_sensor
        self.school.direct_sensor_distance = Decimal("50.0")
        self.school.save()
        
        result = self.school.get_current_reading()
        self.assertEqual(result['method'], 'direct')
        self.assertEqual(result['no2'], Decimal("25.0"))
        self.assertEqual(result['pm25'], Decimal("8.5"))
        self.assertEqual(result['pm10'], Decimal("15.0"))
    
    def test_adjusted_reading_calculation(self):
        """Test LAEI baseline adjusted by current sensor readings"""
        result = self.school.get_current_reading()
        
        # Should use adjusted method
        self.assertEqual(result['method'], 'laei_adjusted')
        
        # Adjustment factor should be 1.2 (48.0/40.0)
        # LAEI baseline 30.0 * 1.2 = 36.0
        self.assertAlmostEqual(float(result['no2']), 36.0, places=1)
        
        # PM2.5: 10.0 * 1.2 = 12.0
        self.assertAlmostEqual(float(result['pm25']), 12.0, places=1)
        
        # PM10: 18.0 * 1.2 = 21.6
        self.assertAlmostEqual(float(result['pm10']), 21.6, places=1)
    
    def test_adjustment_factor_safety_bounds(self):
        """Test that adjustment factors are capped between 0.2 and 5.0"""
        # Create extreme reading (10x higher than annual mean)
        Reading.objects.filter(sensor=self.laqn_sensor).delete()
        Reading.objects.create(
            sensor=self.laqn_sensor,
            timestamp=timezone.now() - timedelta(hours=1),
            no2=Decimal("400.0"),  # 10x higher (would give factor of 10.0)
            pm25=Decimal("100.0"),
            pm10=Decimal("200.0")
        )
        
        result = self.school.get_current_reading()
        
        # Factor should be capped at 5.0
        # LAEI 30.0 * 5.0 = 150.0 (not 300.0)
        self.assertLessEqual(float(result['no2']), 150.0)
    
    def test_stale_reading_fallback(self):
        """Test that stale readings (>24 hours) fall back to LAEI"""
        # Delete fresh reading, add stale one
        Reading.objects.filter(sensor=self.laqn_sensor).delete()
        Reading.objects.create(
            sensor=self.laqn_sensor,
            timestamp=timezone.now() - timedelta(hours=30),  # 30 hours old
            no2=Decimal("50.0"),
            pm25=Decimal("15.0"),
            pm10=Decimal("25.0")
        )
        
        result = self.school.get_current_reading()
        
        # Should fall back to LAEI baseline
        self.assertEqual(result['method'], 'laei_only')
        self.assertEqual(result['no2'], self.school.no2_2022)
    
    def test_school_hours_indicator(self):
        """Test that school hours indicator is set correctly"""
        # Create nighttime reading
        Reading.objects.filter(sensor=self.laqn_sensor).delete()
        night_time = timezone.now().replace(hour=23, minute=0, second=0, microsecond=0)
        Reading.objects.create(
            sensor=self.laqn_sensor,
            timestamp=night_time,
            no2=Decimal("48.0"),
            pm25=Decimal("12.0"),
            pm10=Decimal("24.0")
        )
        
        result = self.school.get_current_reading()
        
        # Should have is_school_hours flag
        self.assertIn('is_school_hours', result)
        self.assertFalse(result['is_school_hours'])
        self.assertIn('reading_timestamp', result)
    
    def test_missing_annual_stats_fallback(self):
        """Test fallback when annual stats are missing"""
        # Delete annual stats
        SensorAnnualStats.objects.filter(sensor=self.laqn_sensor).delete()
        
        result = self.school.get_current_reading()
        
        # Should fall back to LAEI baseline
        self.assertEqual(result['method'], 'laei_only')
    
    def test_no_laei_baseline_returns_none(self):
        """Test that schools without LAEI data return None"""
        school = School.objects.create(
            name="No Data School",
            address="000 Empty St",
            city="London",
            postcode="SE0 0AA",
            latitude=Decimal("51.5000"),
            longitude=Decimal("-0.1000"),
            laei_data_available=False
        )
        
        result = school.get_current_reading()
        self.assertIsNone(result)
