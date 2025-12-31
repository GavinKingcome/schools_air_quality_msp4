from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from schools.models import School

# Create your tests here.
class MapViewTest(TestCase):
    """Test cases for the map view"""
    
    def setUp(self):
        """Create test schools and client"""
        self.client = Client()
        self.school1 = School.objects.create(
            name="School One",
            address="1 Test St",
            city="London",
            postcode="SE1 1AA",
            latitude=Decimal("51.5074"),
            longitude=Decimal("-0.1278"),
            school_type="primary"
        )
        self.school2 = School.objects.create(
            name="School Two",
            address="2 Test Ave",
            city="London",
            postcode="SE2 2BB",
            latitude=Decimal("51.5100"),
            longitude=Decimal("-0.1300"),
            school_type="nursery"
        )
    
    def test_map_view_status(self):
        """Test that the map view returns 200"""
        response = self.client.get(reverse('maps:map'))
        self.assertEqual(response.status_code, 200)
    
    def test_map_view_template(self):
        """Test that the correct template is used"""
        response = self.client.get(reverse('maps:map'))
        self.assertTemplateUsed(response, 'maps/map.html')
    
    def test_map_view_context(self):
        """Test that schools data is passed to template"""
        response = self.client.get(reverse('maps:map'))
        self.assertIn('schools_json', response.context)