from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from .models import School
from air_quality.models import Sensor, Reading, SensorAnnualStats


class SchoolModelBasicTest(TestCase):
    """Test cases for basic School model functionality"""
    
    def setUp(self):
        """Create a test school"""
        self.school = School.objects.create(
            name="Test Primary School",
            address="123 Test Street",
            city="London",
            postcode="SE1 1AA",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            borough="Lambeth",
            school_type="primary",
            student_count=250,
            no2_2022=Decimal("35.5"),
            pm25_2022=Decimal("12.3"),
            pm10_mean_2022=Decimal("18.7"),
            laei_data_available=True
        )
    
    def test_school_creation(self):
        """Test that a school can be created"""
        self.assertEqual(self.school.name, "Test Primary School")
        self.assertEqual(self.school.city, "London")
        self.assertEqual(self.school.school_type, "primary")
        self.assertEqual(self.school.borough, "Lambeth")
    
    def test_school_str_method(self):
        """Test the string representation of a school"""
        self.assertEqual(str(self.school), "Test Primary School")
    
    def test_school_coordinates(self):
        """Test that coordinates are stored correctly"""
        self.assertEqual(self.school.latitude, Decimal("51.5074"))
        self.assertEqual(self.school.longitude, Decimal("-0.1278"))
    
    def test_school_type_choices(self):
        """Test that only valid school types are accepted"""
        self.assertIn(self.school.school_type, ['nursery', 'primary'])
    
    def test_school_laei_baseline_data(self):
        """Test LAEI 2022 baseline data storage"""
        self.assertEqual(self.school.no2_2022, Decimal("35.5"))
        self.assertEqual(self.school.pm25_2022, Decimal("12.3"))
        self.assertEqual(self.school.pm10_mean_2022, Decimal("18.7"))
        self.assertTrue(self.school.laei_data_available)
    
    def test_school_optional_fields(self):
        """Test that optional fields can be null/blank"""
        school = School.objects.create(
            name="Minimal School",
            address="456 Test Ave",
            city="London",
            postcode="SE2 2BB",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            # phone, email, website, student_count are optional
        )
        self.assertIsNone(school.phone)
        self.assertIsNone(school.email)
        self.assertIsNone(school.student_count)