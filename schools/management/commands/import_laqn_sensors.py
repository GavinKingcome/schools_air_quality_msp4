"""
Import LAQN sensor metadata from London Air Quality Network API.

Usage:
    python manage.py import_laqn_sensors
"""

import requests
from django.core.management.base import BaseCommand
from schools.models import Sensor


class Command(BaseCommand):
    help = 'Import LAQN sensor locations from API'
    
    API_URL = 'https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSiteSpecies/GroupName=London/Json'
    
    def handle(self, *args, **options):
        self.stdout.write('Fetching LAQN sensor data...')
        
        try:
            response = requests.get(self.API_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'Sites' not in data or 'Site' not in data['Sites']:
                self.stdout.write(self.style.ERROR('Unexpected API response structure'))
                return
            
            sites = data['Sites']['Site']
            created_count = 0
            updated_count = 0
            
            for site in sites:
                site_code = site.get('@SiteCode')
                site_name = site.get('@SiteName')
                latitude = site.get('@Latitude')
                longitude = site.get('@Longitude')
                site_type = site.get('@SiteType', '').lower().replace(' ', '_')
                borough = site.get('@LocalAuthorityName', '')
                
                if not all([site_code, site_name, latitude, longitude]):
                    continue
                
                # Map LAQN site types to our choices
                site_type_mapping = {
                    'roadside': 'roadside',
                    'kerbside': 'kerbside',
                    'urban_background': 'urban_background',
                    'suburban': 'suburban',
                    'industrial': 'industrial',
                }
                mapped_type = site_type_mapping.get(site_type, 'urban_background')
                
                # Create or update sensor
                sensor, created = Sensor.objects.update_or_create(
                    site_code=site_code,
                    defaults={
                        'name': site_name,
                        'latitude': latitude,
                        'longitude': longitude,
                        'network': 'LAQN',
                        'site_type': mapped_type,
                        'borough': borough,
                        'is_active': True,
                        'metadata': {
                            'original_site_type': site.get('@SiteType'),
                            'site_link': site.get('@SiteLink'),
                        }
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f'  ✓ Created: {site_code} - {site_name}')
                else:
                    updated_count += 1
                    self.stdout.write(f'  ↻ Updated: {site_code} - {site_name}')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nComplete! Created: {created_count}, Updated: {updated_count}'
                )
            )
        
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'API request failed: {e}'))