"""
Django management command to sync Air Quality England (AQE) sensors.

Usage:
    python manage.py sync_aqe_sensors
    python manage.py sync_aqe_sensors --borough=Southwark
    python manage.py sync_aqe_sensors --show-columns     # first run: check field names

After syncing, links the old LAQN codes for Southwark's migrated stations
to their new AQE codes, so history and current data can be joined.
"""

from django.core.management.base import BaseCommand
from air_quality.models import Sensor
from air_quality.services.aqe_api import AQEApi
import pandas as pd
import logging

logger = logging.getLogger(__name__)


# Old LAQN code -> new AQE code for Southwark stations that moved in
# March 2025. The first four are confirmed from both websites. Elephant
# and Castle and Vicarage Grove were not visible on AQE when checked, so
# confirm those codes before adding them.
SUCCESSORS = {
    'SK8': 'SWK08',   # Tower Bridge Road
    'SK9': 'SWK09',   # A2 Old Kent Road FIDAS
    'SKA': 'SWK10',   # Lower Road
    'SKC': 'SWK12',   # South Circular Road
    # 'SK6': 'SWK06', # Elephant and Castle  (unconfirmed)
    # 'SKB': 'SWK11', # Vicarage Grove       (unconfirmed)
}


def map_site_type(raw: str) -> str:
    """Map Ricardo's site type labels to our choices."""
    raw = (raw or '').lower()
    if 'kerb' in raw or 'traffic' in raw or 'roadside' in raw:
        return 'roadside'
    if 'industrial' in raw:
        return 'industrial'
    if 'suburban' in raw:
        return 'suburban'
    return 'urban_background'


def to_date(value):
    """Turn a metadata date (string, Timestamp or NaN) into a date or None."""
    if value is None:
        return None
    try:
        ts = pd.to_datetime(value)
    except (ValueError, TypeError):
        return None
    if pd.isna(ts):
        return None
    return ts.date()


class Command(BaseCommand):
    help = 'Sync Air Quality England monitoring sites from the Ricardo metadata file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--borough',
            action='append',
            type=str,
            help='Borough to sync (can be given more than once). Default: Lambeth, Southwark',
        )
        parser.add_argument(
            '--show-columns',
            action='store_true',
            help='Print the metadata column names and first rows, then stop',
        )

    def handle(self, *args, **options):
        api = AQEApi()

        if options['show_columns']:
            meta = api.get_metadata()
            if meta is None:
                self.stderr.write(self.style.ERROR('Could not fetch metadata'))
                return
            self.stdout.write('Columns: ' + ', '.join(meta.columns))
            self.stdout.write(meta.head(10).to_string())
            return

        boroughs = options.get('borough') or ['Lambeth', 'Southwark']
        self.stdout.write(f'Syncing AQE sensors for: {", ".join(boroughs)}')

        try:
            sites = api.get_sites(local_authorities=boroughs)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'AQE metadata error: {e}'))
            return

        self.stdout.write(f'Found {len(sites)} AQE sites')

        created_count = 0
        updated_count = 0

        for site in sites:
            site_code = site.get('code')
            latitude = site.get('latitude')
            longitude = site.get('longitude')

            if not site_code or pd.isna(latitude) or pd.isna(longitude):
                logger.warning(f'Skipping AQE site with missing data: {site}')
                continue

            date_opened = to_date(site.get('start_date'))
            date_closed = to_date(site.get('end_date'))

            sensor, created = Sensor.objects.update_or_create(
                site_code=site_code,
                defaults={
                    'name': str(site.get('site', site_code))[:200],
                    'latitude': float(latitude),
                    'longitude': float(longitude),
                    'network': 'AQE',
                    'site_type': map_site_type(site.get('site_type')),
                    'borough': site.get('local_authority', ''),
                    'date_opened': date_opened,
                    'date_closed': date_closed,
                    'is_active': date_closed is None,
                    'metadata': {
                        'site_type_raw': site.get('site_type'),
                        'zone': site.get('zone'),
                        'agglomeration': site.get('agglomeration'),
                    },
                },
            )

            status = 'closed' if date_closed else 'active'
            if created:
                created_count += 1
                self.stdout.write(f'  + Created: {sensor.site_code} {sensor.name} ({status})')
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'\nSync complete: {created_count} created, {updated_count} updated')
        )

        self._link_successors()

        # Summary
        active = Sensor.objects.filter(network='AQE', is_active=True).count()
        total = Sensor.objects.filter(network='AQE').count()
        self.stdout.write(f'AQE sensors: {active} active, {total} total')

    def _link_successors(self):
        """Point each migrated LAQN sensor at its AQE replacement."""
        linked = 0
        for old_code, new_code in SUCCESSORS.items():
            old = Sensor.objects.filter(site_code=old_code, network='LAQN').first()
            new = Sensor.objects.filter(site_code=new_code, network='AQE').first()
            if old and new and old.successor_id != new.id:
                old.successor = new
                old.save(update_fields=['successor'])
                linked += 1
                self.stdout.write(f'  Linked {old_code} (LAQN) -> {new_code} (AQE)')
        if linked:
            self.stdout.write(self.style.SUCCESS(f'{linked} successor links set'))
