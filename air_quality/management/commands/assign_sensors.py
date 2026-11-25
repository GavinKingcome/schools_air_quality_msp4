"""
Django management command to assign sensors to schools.

For each school it decides:
1. Direct sensor: the nearest urban background sensor within 150 m.
   Its reading is used as measured at the school.
2. Sensor list: up to 6 nearby sensors (within 2 km) that have reported
   in the last 7 days and have a yearly average, saved as SchoolSensor
   rows in ranked order:
     - urban background sensors first, then other site types
       (site type comes before network, decided 22 November 2026)
     - nearest first within each group, whatever the network
   A school's own direct sensor is never on its list.
   When a page opens, each pollutant uses the first sensor on the list
   with a fresh reading and a yearly average for that pollutant.
3. Data source: DIRECT (has a direct sensor), ADJUSTED (has a list)
   or LAEI (nothing in range).

reference_sensor is kept, set to the first sensor on the list, until
get_current_reading uses the lists.

Usage:
    python manage.py assign_sensors --dry-run
    python manage.py assign_sensors
    python manage.py assign_sensors --direct-threshold=150 --reference-threshold=2000 --list-size=6
"""

from collections import Counter
from datetime import timedelta
import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from air_quality.models import Sensor
from air_quality.geo import haversine_distance
from schools.models import School, SchoolSensor

logger = logging.getLogger(__name__)


def rank_key(entry):
    """Urban background first, then other site types; nearest first in each."""
    is_background = entry['sensor'].site_type == 'urban_background'
    return (0 if is_background else 1, entry['distance'])


def describe(sensor):
    """e.g. 'reference, urban background' -- used for the summary counts."""
    network = 'reference' if sensor.network in Sensor.REFERENCE_NETWORKS else 'Breathe'
    kind = 'urban background' if sensor.site_type == 'urban_background' else 'roadside or other'
    return f'{network}, {kind}'


class Command(BaseCommand):
    help = 'Assign each school a direct sensor (if any) and a ranked list of nearby sensors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--direct-threshold',
            type=int,
            default=150,
            help='Maximum distance (m) for a direct sensor (default: 150)'
        )
        parser.add_argument(
            '--reference-threshold',
            type=int,
            default=2000,
            help='Maximum distance (m) for a sensor on the list (default: 2000)'
        )
        parser.add_argument(
            '--list-size',
            type=int,
            default=6,
            help='Most sensors kept on each school\'s list (default: 6)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without saving'
        )

    def handle(self, *args, **options):
        direct_threshold = options['direct_threshold']
        list_threshold = options['reference_threshold']
        list_size = options['list_size']
        dry_run = options['dry_run']

        schools = list(School.objects.all())
        total = len(schools)

        # Only sensors that have sent a reading in the last 7 days.
        # A site can be officially open but silent (e.g. LB5).
        recent = timezone.now() - timedelta(days=7)
        recent_sensors = list(
            Sensor.objects.filter(is_active=True, readings__timestamp__gte=recent).distinct()
        )

        # A sensor on a list also needs a yearly average, since the
        # adjustment needs one (reading now ÷ yearly average).
        with_average = set(
            Sensor.objects.filter(
                id__in=[s.id for s in recent_sensors],
                annual_stats__isnull=False,
            ).values_list('id', flat=True)
        )
        usable = Counter(
            describe(s).split(',')[0] for s in recent_sensors if s.id in with_average
        )

        self.stdout.write('\nSensor Assignment')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Schools to process: {total}')
        self.stdout.write(f'Sensors that reported in the last 7 days: {len(recent_sensors)}')
        self.stdout.write(
            f'  ...of which have a yearly average: {len(with_average)} '
            f'({usable["reference"]} reference, {usable["Breathe"]} Breathe)'
        )
        self.stdout.write(f'Direct sensor: urban background, within {direct_threshold} m')
        self.stdout.write(
            f'Sensor list: up to {list_size} within {list_threshold} m, '
            f'urban background first, then nearest'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('\n** DRY RUN - no changes will be saved **\n'))

        stats = Counter()          # data sources
        first_choice = Counter()   # what kind of sensor is first on each list
        list_lengths = Counter()   # how many sensors each list has
        updated_schools = []
        new_rows = []

        for school in schools:
            if not school.latitude or not school.longitude:
                logger.warning(f'School {school.name} has no coordinates')
                continue

            distances = sorted(
                (
                    {
                        'sensor': sensor,
                        'distance': haversine_distance(
                            school.latitude, school.longitude,
                            sensor.latitude, sensor.longitude,
                        ),
                    }
                    for sensor in recent_sensors
                ),
                key=lambda e: e['distance'],
            )

            # === DIRECT SENSOR ===
            # The nearest urban background sensor within the direct threshold
            direct = next(
                (e for e in distances
                 if e['distance'] <= direct_threshold
                 and e['sensor'].site_type == 'urban_background'),
                None,
            )
            direct_sensor = direct['sensor'] if direct else None

            # === SENSOR LIST ===
            # Within range, with a yearly average, never the school's own
            # direct sensor (it would go quiet at the same time).
            candidates = [
                e for e in distances
                if e['distance'] <= list_threshold
                and e['sensor'].id in with_average
                and e['sensor'] != direct_sensor
            ]
            candidates.sort(key=rank_key)
            ranked = candidates[:list_size]
            first = ranked[0] if ranked else None
            list_lengths[len(ranked)] += 1

            # === DATA SOURCE ===
            if direct_sensor:
                data_source = 'DIRECT'
            elif first:
                data_source = 'ADJUSTED'
            else:
                data_source = 'LAEI'
            stats[data_source] += 1
            if first:
                first_choice[describe(first['sensor'])] += 1

            if direct_sensor:
                self.stdout.write(
                    f'  ✓ DIRECT: {school.name[:40]:<40} ← '
                    f'{direct_sensor.site_code} ({direct["distance"]:.1f}m, {direct_sensor.network})'
                )

            # === PREPARE THE SAVE ===
            school.direct_sensor = direct_sensor
            school.direct_sensor_distance = round(direct['distance'], 1) if direct else None
            school.reference_sensor = first['sensor'] if first else None
            school.reference_sensor_distance = round(first['distance'], 1) if first else None
            school.data_source = data_source
            updated_schools.append(school)

            new_rows.extend(
                SchoolSensor(
                    school=school,
                    sensor=e['sensor'],
                    rank=rank,
                    distance_m=round(e['distance'], 1),
                )
                for rank, e in enumerate(ranked, start=1)
            )

        # === SAVE ===
        # All in one transaction: either every school and list is updated,
        # or nothing is (the page never sees half-rebuilt lists).
        if not dry_run:
            with transaction.atomic():
                School.objects.bulk_update(
                    updated_schools,
                    ['direct_sensor', 'direct_sensor_distance',
                     'reference_sensor', 'reference_sensor_distance', 'data_source'],
                )
                SchoolSensor.objects.all().delete()
                SchoolSensor.objects.bulk_create(new_rows)

        # === SUMMARY ===
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Assignment Summary'))
        self.stdout.write('=' * 50)

        self.stdout.write('\nData source breakdown:')
        for key, label in [
            ('DIRECT', f'DIRECT (urban background sensor within {direct_threshold} m)'),
            ('ADJUSTED', 'ADJUSTED (LAEI x a sensor on the list)'),
            ('LAEI', 'LAEI ONLY (no sensor in range)'),
        ]:
            self.stdout.write(f'  {label:<50} {stats[key]:3d} ({100 * stats[key] / total:.1f}%)')

        self.stdout.write('\nFirst sensor on each list:')
        for kind in ['reference, urban background', 'Breathe, urban background',
                     'reference, roadside or other', 'Breathe, roadside or other']:
            self.stdout.write(f'  {kind:<50} {first_choice[kind]:3d}')

        self.stdout.write('\nSchools by number of sensors on their list:')
        for n in range(list_size + 1):
            self.stdout.write(f'  {n} sensor{"" if n == 1 else "s"}: {list_lengths[n]:3d}')
        self.stdout.write(f'  Total list entries: {len(new_rows)}')

        self.stdout.write('\n' + '-' * 50)
        self.stdout.write('Methodology:')
        self.stdout.write('  • DIRECT: sensor reading used as measured at the school')
        self.stdout.write('  • ADJUSTED: LAEI baseline x (sensor now / sensor yearly average)')
        self.stdout.write('  • LAEI ONLY: modelled 2022 annual average')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n** DRY RUN - no changes saved **'))