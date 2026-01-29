from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import json
from schools.models import School
from air_quality.models import Sensor, Reading, SensorAnnualStats


class MapViewTest(TestCase):
    """Test cases for the map view"""
    
    def setUp(self):
        """Create test schools, sensors, and client"""
        self.client = Client()
        
        # Create sensor with data
        self.sensor = Sensor.objects.create(
            name="Test Sensor",
            site_code="TEST01",
            network="LAQN",
            latitude=Decimal("51.5100"),
            longitude=Decimal("-0.1300"),
            is_active=True
        )
        
        SensorAnnualStats.objects.create(
            sensor=self.sensor,
            year=2024,
            no2_mean=Decimal("40.0"),
            pm25_mean=Decimal("10.0"),
            pm10_mean=Decimal("20.0")
        )
        
        Reading.objects.create(
            sensor=self.sensor,
            timestamp=timezone.now() - timedelta(hours=1),
            no2=Decimal("48.0"),
            pm25=Decimal("12.0"),
            pm10=Decimal("24.0")
        )
        
        # Create schools with different data sources
        self.school1 = School.objects.create(
            name="School One",
            address="1 Test St",
            city="London",
            postcode="SE1 1AA",
            borough="Lambeth",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            school_type="primary",
            no2_2022=Decimal("30.0"),
            pm25_2022=Decimal("10.0"),
            pm10_mean_2022=Decimal("18.0"),
            laei_data_available=True,
            data_source='ADJUSTED',
            reference_sensor=self.sensor,
            reference_sensor_distance=Decimal("500.0")
        )
        
        self.school2 = School.objects.create(
            name="School Two",
            address="2 Test Ave",
            city="London",
            postcode="SE2 2BB",
            borough="Southwark",
            latitude=Decimal("51.5100"),
            longitude=Decimal("-0.1300"),
            school_type="nursery",
            no2_2022=Decimal("25.0"),
            pm25_2022=Decimal("8.0"),
            pm10_mean_2022=Decimal("15.0"),
            laei_data_available=True,
            data_source='LAEI'
        )
    
    def test_map_view_status(self):
        """Test that the map view returns 200"""
        response = self.client.get(reverse('maps:map'))
        self.assertEqual(response.status_code, 200)
    
    def test_map_view_template(self):
        """Test that the correct template is used"""
        response = self.client.get(reverse('maps:map'))
        self.assertTemplateUsed(response, 'maps/map.html')
    
    def test_map_view_context_has_schools(self):
        """Test that schools data is passed to template"""
        response = self.client.get(reverse('maps:map'))
        self.assertIn('schools_json', response.context)
        
        # Parse JSON and check structure
        schools_data = json.loads(response.context['schools_json'])
        self.assertEqual(len(schools_data), 2)
    
    def test_map_view_context_has_sensors(self):
        """Test that sensors data is passed to template"""
        response = self.client.get(reverse('maps:map'))
        self.assertIn('sensors_json', response.context)
        
        sensors_data = json.loads(response.context['sensors_json'])
        self.assertGreaterEqual(len(sensors_data), 1)
    
    def test_school_json_structure(self):
        """Test that school JSON contains required fields"""
        response = self.client.get(reverse('maps:map'))
        schools_data = json.loads(response.context['schools_json'])
        
        school = schools_data[0]
        required_fields = ['name', 'latitude', 'longitude', 'borough', 
                          'data_source', 'no2', 'pm25', 'pm10']
        
        for field in required_fields:
            self.assertIn(field, school)
    
    def test_sensor_json_structure(self):
        """Test that sensor JSON contains required fields"""
        response = self.client.get(reverse('maps:map'))
        sensors_data = json.loads(response.context['sensors_json'])
        
        if sensors_data:
            sensor = sensors_data[0]
            required_fields = ['name', 'site_code', 'network', 
                             'latitude', 'longitude']
            
            for field in required_fields:
                self.assertIn(field, sensor)
    
    def test_adjusted_school_data_in_view(self):
        """Test that adjusted schools show correct data source"""
        response = self.client.get(reverse('maps:map'))
        schools_data = json.loads(response.context['schools_json'])
        
        # Find School One (adjusted)
        school_one = next(s for s in schools_data if s['name'] == 'School One')
        self.assertEqual(school_one['data_source'], 'ADJUSTED')
        self.assertIsNotNone(school_one['reference_sensor'])
    
    def test_laei_school_data_in_view(self):
        """Test that LAEI-only schools show correct data source"""
        response = self.client.get(reverse('maps:map'))
        schools_data = json.loads(response.context['schools_json'])
        
        # Find School Two (LAEI only)
        school_two = next(s for s in schools_data if s['name'] == 'School Two')
        self.assertEqual(school_two['data_source'], 'LAEI')
    
    def test_map_view_no_schools(self):
        """Test map view works when no schools exist"""
        School.objects.all().delete()
        response = self.client.get(reverse('maps:map'))
        self.assertEqual(response.status_code, 200)
        
        schools_data = json.loads(response.context['schools_json'])
        self.assertEqual(len(schools_data), 0)