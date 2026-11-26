"""
Django management command to sync LAQN sensors.

By default it syncs every site in Lambeth and Southwark, plus open sites
in any other borough that are within 2 km of one of our schools.

Usage:
    python manage.py sync_laqn_sensors
    python manage.py sync_laqn_sensors --borough=Lambeth --borough=Southwark
    python manage.py sync_laqn_sensors --all
"""

from django.core.management.base import BaseCommand
from air_quality.models import Sensor
from air_quality.services.laqn_api import LAQNApi
from air_quality.geo import HOME_BOROUGHS, NEARBY_METRES, near_any_school, school_locations
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_laqn_date(value):
    """'2025-03-31 00:00:00' -> date(2025, 3, 31); '' -> None."""
    if not value:
        return None
    return datetime.strptime(value[:10], "%Y-%m-%d").date()

class Command(BaseCommand):
    help = 'Sync LAQN monitoring sites from the London Air API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--borough',
            action='append',
            type=str,
            help='Only sync sites in this borough (can be given several times)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync every London site'
        )
    
    def handle(self, *args, **options):
        api = LAQNApi()
        boroughs = options.get('borough') or []

        # One call returns every London site
        try:
            all_sites = api.get_monitoring_sites()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error fetching London sites: {e}'))
            return

        if options['all']:
            sites = all_sites
            self.stdout.write(f'Syncing all {len(sites)} London LAQN sites')
        elif boroughs:
            wanted = {b.lower() for b in boroughs}
            sites = [s for s in all_sites
                     if s.get('@LocalAuthorityName', '').lower() in wanted]
            self.stdout.write(f'Syncing LAQN sites in {", ".join(boroughs)}: {len(sites)} found')
        else:
            schools = school_locations()
            sites = [s for s in all_sites if self._wanted(s, schools)]
            self.stdout.write(
                f'Syncing LAQN sites in Lambeth and Southwark, plus open sites '
                f'within {NEARBY_METRES} m of a school: {len(sites)} found'
            )

        created_count = 0
        updated_count = 0

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
                
            date_opened = parse_laqn_date(site.get('@DateOpened'))
            date_closed = parse_laqn_date(site.get('@DateClosed'))
            
            # Create or update
            sensor, created = Sensor.objects.update_or_create(
                site_code=site_code,
                defaults={
                    'name': site.get('@SiteName', site_code),
                    'latitude': latitude,
                    'longitude': longitude,
                    'network': 'LAQN',
                    'site_type': site_type,
                    'borough': site.get('@LocalAuthorityName', ''),
                    'date_opened': date_opened,
                    'date_closed': date_closed,
                    'is_active': date_closed is None,
                    'metadata': {
                        'local_authority_id': site.get('@LocalAuthorityId'),
                        'site_link': site.get('@SiteLink'),
                        'data_owner': site.get('@DataOwner'),
                    }
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    f'  + Created: {site_code} {sensor.name} ({sensor.borough}, {site_type})'
                )
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

    def _wanted(self, site, schools):
        """Every site in the home boroughs; elsewhere, open sites near a school."""
        if site.get('@LocalAuthorityName', '').lower() in HOME_BOROUGHS:
            return True
        if site.get('@DateClosed'):
            return False  # a closed site in another borough is no use to us
        try:
            lat, lon = float(site['@Latitude']), float(site['@Longitude'])
        except (KeyError, TypeError, ValueError):
            return False
        return near_any_school(lat, lon, schools)