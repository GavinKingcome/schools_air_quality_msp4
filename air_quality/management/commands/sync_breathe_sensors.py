"""
Django management command to sync Breathe London sensors.

By default it syncs every site in Lambeth and Southwark, plus running
sites in any other borough that are within 2 km of one of our schools.

Usage:
    python manage.py sync_breathe_sensors
    python manage.py sync_breathe_sensors --borough=Lambeth --borough=Southwark
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from air_quality.models import Sensor
from air_quality.services.breathe_london_api import BreatheLondonApi
from air_quality.geo import HOME_BOROUGHS, NEARBY_METRES, near_any_school, school_locations
import logging

logger = logging.getLogger(__name__)

def is_newer(a, b):
    """True if installation a should replace installation b."""
    a_running = a.get('EndDate') is None
    b_running = b.get('EndDate') is None
    if a_running != b_running:
        return a_running          # one still running beats one that ended
    # Otherwise the later start wins. The dates are text like
    # '2025-03-07T00:00:00Z', which sort correctly as text.
    return (a.get('StartDate'))

class Command(BaseCommand):
    help = 'Sync Breathe London sensor locations from OpenAQ API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--borough',
            action='append',
            type=str,
            help='Only sync sites in this borough (can be given several times)'
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
        
        # Either the boroughs asked for, or every sensor in one call
        boroughs = options.get('borough')
        try:
            if boroughs:
                self.stdout.write(f'Fetching Breathe London sensors for: {", ".join(boroughs)}')
                sensors = api.get_sensors_by_borough(boroughs)
            else:
                self.stdout.write('Fetching all Breathe London sensors')
                sensors = api.get_all_sensors()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'API error: {e}'))
            return
        
        # The API lists each site's past installations too, all under the
        # same site code. Keep only the current one for each site.
        current = {}
        for s in sensors:
            code = s.get('SiteCode')
            if not code:
                continue
            kept = current.get(code)
            if kept is None or is_newer(s, kept):
                current[code] = s
        
        self.stdout.write(
            f'Found {len(sensors)} installations for {len(current)} Breathe London sites'
        )
        sensors = list(current.values())

        # Without --borough: keep Lambeth and Southwark, plus running
        # sites elsewhere within 2 km of one of our schools
        if not boroughs:
            schools = school_locations()
            sensors = [s for s in sensors if self._wanted(s, schools)]
            self.stdout.write(
                f'Keeping {len(sensors)}: Lambeth and Southwark, plus running sites '
                f'within {NEARBY_METRES} m of a school'
            )
        
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
    
    def _wanted(self, sensor_data, schools):
        """Every site in the home boroughs; elsewhere, running sites near a school."""
        if (sensor_data.get('Borough') or '').lower() in HOME_BOROUGHS:
            return True
        if sensor_data.get('EndDate') is not None:
            return False  # an ended site in another borough is no use to us
        try:
            lat = float(sensor_data['Latitude'])
            lon = float(sensor_data['Longitude'])
        except (KeyError, TypeError, ValueError):
            return False
        return near_any_school(lat, lon, schools)

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
