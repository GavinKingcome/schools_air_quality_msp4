"""
Django management command to sync Breathe London sensors.

Usage:
    python manage.py sync_breathe_sensors
    python manage.py sync_breathe_sensors --bbox=-0.15,51.41,-0.03,51.50
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from air_quality.models import Sensor
from air_quality.services.breathe_london_api import BreatheLondonApi
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Breathe London sensor locations from OpenAQ API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--borough',
            action='append',
            type=str,
            help='Borough to sync (can be specified multiple times, default: Lambeth, Southwark)'
        )
    
    def handle(self, *args, **options):
        api_key = getattr(settings, 'BREATHE_LONDON_API_KEY', None)
        
        if not api_key:
            self.stderr.write(
                self.style.ERROR(
                    'BREATHE_LONDON_API_KEY not found in settings. '
                    'Add it to your .env or settings.py'
                )
            )
            return
        
        api = BreatheLondonApi(api_key)
        
        # Determine boroughs
        boroughs = options.get('borough') or ['Lambeth', 'Southwark']
        self.stdout.write(f'Fetching Breathe London sensors for: {", ".join(boroughs)}')
        
        try:
            sensors = api.get_sensors_by_borough(boroughs)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'API error: {e}'))
            return
        
        self.stdout.write(f'Found {len(sensors)} Breathe London sensors')
        
        created_count = 0
        updated_count = 0
        
        for sensor_data in sensors:
            # Extract sensor data from Breathe London API response
            site_code = sensor_data.get('SiteCode')
            name = sensor_data.get('SiteName', site_code)
            latitude = sensor_data.get('Latitude')
            longitude = sensor_data.get('Longitude')
            borough = sensor_data.get('Borough', '')
            
            if not all([site_code, latitude, longitude]):
                logger.warning(f'Skipping sensor with missing data: {sensor_data}')
                continue
            
            # Determine site type from classification
            site_classification = sensor_data.get('SiteClassification', '').lower()
            if 'roadside' in site_classification or 'kerb' in site_classification:
                site_type = 'roadside'
            elif 'background' in site_classification:
                site_type = 'urban_background'
            else:
                site_type = 'urban_background'  # Default
            
            # Create or update sensor
            sensor, created = Sensor.objects.update_or_create(
                site_code=site_code,
                defaults={
                    'name': name[:200],
                    'latitude': float(latitude),
                    'longitude': float(longitude),
                    'network': 'BREATHE',
                    'site_type': site_type,
                    'borough': borough,
                    'is_active': sensor_data.get('EndDate') is None,
                    'metadata': {
                        'device_code': sensor_data.get('DeviceCode'),
                        'installation_code': sensor_data.get('InstallationCode'),
                        'facility': sensor_data.get('Facility'),
                        'sponsor': sensor_data.get('SponsorName'),
                        'site_type': sensor_data.get('SiteLocationType'),
                        'start_date': sensor_data.get('StartDate'),
                        'end_date': sensor_data.get('EndDate'),
                        'photo_url': sensor_data.get('SitePhotoURL'),
                    }
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  + Created: {sensor.name}')
            else:
                updated_count += 1
        
        # Mark sensors not in current fetch as potentially inactive
        # (but don't auto-deactivate in case of API issues)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSync complete: {created_count} created, {updated_count} updated'
            )
        )
        
        # Summary of sensor coverage
        total_breathe = Sensor.objects.filter(network='BREATHE', is_active=True).count()
        total_laqn = Sensor.objects.filter(network='LAQN', is_active=True).count()
        self.stdout.write(f'\nTotal active sensors:')
        self.stdout.write(f'  LAQN (reference): {total_laqn}')
        self.stdout.write(f'  Breathe London:   {total_breathe}')
        self.stdout.write(f'  Combined:         {total_laqn + total_breathe}')
    
    def _determine_site_type(self, location: dict) -> str:
        """
        Determine site type from location metadata.
        
        Breathe London sensors are typically classified based on their
        proximity to roads and traffic.
        """
        name = location.get('name', '').lower()
        
        # Check name for hints
        if any(word in name for word in ['road', 'street', 'junction', 'a2', 'a3', 'a23']):
            return 'roadside'
        elif any(word in name for word in ['park', 'garden', 'school', 'residential']):
            return 'urban_background'
        elif any(word in name for word in ['industrial', 'depot', 'works']):
            return 'industrial'
        
        # Default to urban background (most common for Breathe London)
        return 'urban_background'
