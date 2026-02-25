from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from .models import Sensor, Reading, SensorAnnualStats


class SensorModelTest(TestCase):
    """Test cases for Sensor model"""
    
    def setUp(self):
        """Create test sensors"""
        self.laqn_sensor = Sensor.objects.create(
            name="Lambeth - Test Road",
            site_code="LB99",
            network="LAQN",
            latitude=Decimal("51.5100"),
            longitude=Decimal("-0.1300"),
            site_type="Roadside",
            is_active=True
        )
        
        self.breathe_sensor = Sensor.objects.create(
            name="Test BREATHE Sensor",
            site_code="BL0001",
            network="BREATHE",
            latitude=Decimal("51.5200"),
            longitude=Decimal("-0.1400"),
            site_type="Urban Background",
            is_active=True
        )
    
    def test_sensor_creation(self):
        """Test sensor can be created with required fields"""
        self.assertEqual(self.laqn_sensor.name, "Lambeth - Test Road")
        self.assertEqual(self.laqn_sensor.site_code, "LB99")
        self.assertEqual(self.laqn_sensor.network, "LAQN")
        self.assertTrue(self.laqn_sensor.is_active)
    
    def test_sensor_str_method(self):
        """Test string representation"""
        result = str(self.laqn_sensor)
        self.assertIn("Lambeth - Test Road", result)
        self.assertIn("LAQN", result)
    
    def test_sensor_network_choices(self):
        """Test network is one of valid choices"""
        self.assertIn(self.laqn_sensor.network, ['LAQN', 'BREATHE'])
        self.assertIn(self.breathe_sensor.network, ['LAQN', 'BREATHE'])
    
    def test_sensor_coordinates(self):
        """Test coordinates are stored correctly"""
        self.assertEqual(self.laqn_sensor.latitude, Decimal("51.5100"))
        self.assertEqual(self.laqn_sensor.longitude, Decimal("-0.1300"))
    
    def test_get_latest_reading_with_data(self):
        """Test getting latest reading when readings exist"""
        # Create readings
        older_reading = Reading.objects.create(
            sensor=self.laqn_sensor,
            timestamp=timezone.now() - timedelta(hours=2),
            no2=Decimal("30.0"),
            pm25=Decimal("8.0"),
            pm10=Decimal("15.0")
        )
        
        newer_reading = Reading.objects.create(
            sensor=self.laqn_sensor,
            timestamp=timezone.now() - timedelta(hours=1),
            no2=Decimal("35.0"),
            pm25=Decimal("10.0"),
            pm10=Decimal("18.0")
        )
        
        latest = self.laqn_sensor.get_latest_reading()
        self.assertEqual(latest, newer_reading)
        self.assertEqual(latest.no2, Decimal("35.0"))
    
    def test_get_latest_reading_no_data(self):
        """Test getting latest reading when no readings exist"""
        latest = self.breathe_sensor.get_latest_reading()
        self.assertIsNone(latest)


class ReadingModelTest(TestCase):
    """Test cases for Reading model"""
    
    def setUp(self):
        """Create test sensor and readings"""
        self.sensor = Sensor.objects.create(
            name="Test Sensor",
            site_code="TEST01",
            network="LAQN",
            latitude=Decimal("51.5000"),
            longitude=Decimal("-0.1000"),
            is_active=True
        )
        
        self.reading = Reading.objects.create(
            sensor=self.sensor,
            timestamp=timezone.now() - timedelta(hours=1),
            no2=Decimal("42.5"),
            pm25=Decimal("11.3"),
            pm10=Decimal("19.7")
        )
    
    def test_reading_creation(self):
        """Test reading can be created"""
        self.assertEqual(self.reading.sensor, self.sensor)
        self.assertEqual(self.reading.no2, Decimal("42.5"))
        self.assertEqual(self.reading.pm25, Decimal("11.3"))
        self.assertEqual(self.reading.pm10, Decimal("19.7"))
    
    def test_reading_str_method(self):
        """Test string representation"""
        result = str(self.reading)
        self.assertIn("TEST01", result)
    
    def test_reading_ordering(self):
        """Test readings are ordered by timestamp descending"""
        # Create multiple readings
        older = Reading.objects.create(
            sensor=self.sensor,
            timestamp=timezone.now() - timedelta(hours=5),
            no2=Decimal("30.0")
        )
        
        newer = Reading.objects.create(
            sensor=self.sensor,
            timestamp=timezone.now() - timedelta(hours=1),
            no2=Decimal("40.0")
        )
        
        readings = Reading.objects.all()
        self.assertEqual(readings[0], newer)  # Newest first
        self.assertEqual(readings[2], older)  # Oldest last
    
    def test_reading_unique_constraint(self):
        """Test that sensor+timestamp combination is unique"""
        from django.db import IntegrityError
        
        # Try to create duplicate reading
        with self.assertRaises(IntegrityError):
            Reading.objects.create(
                sensor=self.sensor,
                timestamp=self.reading.timestamp,
                no2=Decimal("50.0")
            )
    
    def test_reading_optional_pollutants(self):
        """Test that pollutant fields can be null"""
        reading = Reading.objects.create(
            sensor=self.sensor,
            timestamp=timezone.now() - timedelta(hours=2),
            no2=Decimal("35.0")
            # pm25 and pm10 are null
        )
        self.assertIsNotNone(reading.no2)
        self.assertIsNone(reading.pm25)
        self.assertIsNone(reading.pm10)


class SensorAnnualStatsTest(TestCase):
    """Test cases for SensorAnnualStats model"""
    
    def setUp(self):
        """Create test sensor and annual stats"""
        self.sensor = Sensor.objects.create(
            name="Test Sensor",
            site_code="TEST01",
            network="LAQN",
            latitude=Decimal("51.5000"),
            longitude=Decimal("-0.1000"),
            is_active=True
        )
        
        self.stats_2024 = SensorAnnualStats.objects.create(
            sensor=self.sensor,
            year=2024,
            no2_mean=Decimal("38.5"),
            pm25_mean=Decimal("10.2"),
            pm10_mean=Decimal("18.9")
        )
        
        self.stats_2023 = SensorAnnualStats.objects.create(
            sensor=self.sensor,
            year=2023,
            no2_mean=Decimal("40.1"),
            pm25_mean=Decimal("11.5"),
            pm10_mean=Decimal("20.3")
        )
    
    def test_annual_stats_creation(self):
        """Test annual stats can be created"""
        self.assertEqual(self.stats_2024.sensor, self.sensor)
        self.assertEqual(self.stats_2024.year, 2024)
        self.assertEqual(self.stats_2024.no2_mean, Decimal("38.5"))
    
    def test_annual_stats_str_method(self):
        """Test string representation"""
        result = str(self.stats_2024)
        self.assertIn("TEST01", result)
        self.assertIn("2024", result)
    
    def test_annual_stats_ordering(self):
        """Test stats are ordered by year descending"""
        stats = SensorAnnualStats.objects.filter(sensor=self.sensor)
        self.assertEqual(stats[0].year, 2024)  # Newest first
        self.assertEqual(stats[1].year, 2023)
    
    def test_annual_stats_unique_constraint(self):
        """Test that sensor+year combination is unique"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            SensorAnnualStats.objects.create(
                sensor=self.sensor,
                year=2024,
                no2_mean=Decimal("45.0")
            )
    
    def test_annual_stats_optional_pollutants(self):
        """Test that pollutant means can be null"""
        stats = SensorAnnualStats.objects.create(
            sensor=self.sensor,
            year=2022,
            no2_mean=Decimal("42.0")
            # pm25_mean and pm10_mean are null
        )
        self.assertIsNotNone(stats.no2_mean)
        self.assertIsNone(stats.pm25_mean)
        self.assertIsNone(stats.pm10_mean)

