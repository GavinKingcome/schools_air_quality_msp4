from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from schools.models import School
from .models import AirQualityReading

# Create your tests here.
class AirQualityReadingModelTest(TestCase):
    """Test cases for the AirQualityReading model"""
    
    def setUp(self):
        """Create a test school and air quality reading"""
        self.school = School.objects.create(
            name="Test School",
            address="123 Test St",
            city="London",
            postcode="SE1 1AA",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            school_type="primary"
        )
        
        self.reading = AirQualityReading.objects.create(
            school=self.school,
            timestamp=timezone.now(),
            pm25=Decimal("12.5"),
            pm10=Decimal("20.3"),
            no2=Decimal("35.2"),
            aqi=45,
            source="Test API"
        )
    
    def test_reading_creation(self):
        """Test that an air quality reading can be created"""
        self.assertEqual(self.reading.school, self.school)
        self.assertEqual(self.reading.pm25, Decimal("12.5"))
        self.assertEqual(self.reading.aqi, 45)
    
    def test_reading_str_method(self):
        """Test the string representation"""
        self.assertIn(self.school.name, str(self.reading))
    
    def test_reading_school_relationship(self):
        """Test the foreign key relationship"""
        self.assertEqual(self.reading.school.name, "Test School")
        self.assertIn(self.reading, self.school.air_quality_readings.all())
    
    def test_optional_pollutants(self):
        """Test that pollutant fields can be null"""
        reading = AirQualityReading.objects.create(
            school=self.school,
            timestamp=timezone.now(),
            pm25=Decimal("10.0"),
            # Other pollutants are optional
        )
        self.assertIsNone(reading.no2)
        self.assertIsNone(reading.o3)