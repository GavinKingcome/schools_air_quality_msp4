"""
Django management command to sync LAQN sensors.

Usage:
    python manage.py sync_laqn_sensors
    python manage.py sync_laqn_sensors --borough=Lambeth --borough=Southwark
"""

from django.core.management.base import BaseCommand
from air_quality.models import Sensor
from air_quality.services.laqn_api import LAQNApi
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync LAQN monitoring sites from the London Air API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--borough',
            action='append',
            type=str,
            help='Borough to sync (can be specified multiple times)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all London boroughs'
        )
    
    def handle(self, *args, **options):
        api = LAQNApi()
        
        boroughs = options.get('borough') or []
        
        if options['all'] or not boroughs:
            # Default to Lambeth and Southwark for AirAware
            if not boroughs:
                boroughs = ['Lambeth', 'Southwark']
        
        self.stdout.write(f'Syncing LAQN sensors for: {", ".join(boroughs)}')
        
        created_count = 0
        updated_count = 0
        
        for borough in boroughs:  # ['Lambeth', 'Southark']
            try:
                sites = api.get_monitoring_sites(borough=borough)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error fetching {borough}: {e}'))
                continue
            
            self.stdout.write(f'  {borough}: {len(sites)} sites found')
            
            for site in sites:
                site_code = site.get('@SiteCode')
                
                if not site_code:
                    continue
                
                # Parse coordinates
                try:
                    latitude = float(site.get('@Latitude', 0))
                    longitude = float(site.get('@Longitude', 0))
                except (ValueError, TypeError):
                    logger.warning(f'Invalid coordinates for {site_code}')
                    continue
                
                if latitude == 0 or longitude == 0:
                    continue
                
                # Map site type
                site_type_raw = site.get('@SiteType', '').lower()
                if 'roadside' in site_type_raw or 'kerbside' in site_type_raw:
                    site_type = 'roadside'
                elif 'industrial' in site_type_raw:
                    site_type = 'industrial'
                elif 'suburban' in site_type_raw:
                    site_type = 'suburban'
                else:
                    site_type = 'urban_background'
                
                # Create or update
                sensor, created = Sensor.objects.update_or_create(
                    site_code=site_code,
                    defaults={
                        'name': site.get('@SiteName', site_code),
                        'latitude': latitude,
                        'longitude': longitude,
                        'network': 'LAQN',
                        'site_type': site_type,
                        'borough': site.get('@LocalAuthorityName', borough),
                        'is_active': site.get('@IsClosed', 'false').lower() != 'true',
                        'metadata': {
                            'local_authority_id': site.get('@LocalAuthorityId'),
                            'site_link': site.get('@SiteLink'),
                            'data_owner': site.get('@DataOwner'),
                        }
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSync complete: {created_count} created, {updated_count} updated'
            )
        )
        
        # Summary
        total = Sensor.objects.filter(network='LAQN', is_active=True).count()
        self.stdout.write(f'Total active LAQN sensors: {total}')
