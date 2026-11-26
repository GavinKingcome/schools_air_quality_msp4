"""
Show each school's latest figures pollutant by pollutant, with both
estimating methods side by side, before anything changes on screen.

    python manage.py compare_estimates                 # every school, plus a summary
    python manage.py compare_estimates --school "St Mark"
    python manage.py compare_estimates --summary-only

Methods:
  current: LAEI at the school x (reading now / sensor's yearly average)
  third:   reading now x (LAEI at the school / LAEI at the sensor)
The setting ESTIMATE_METHOD chooses which one the app shows ('current'
unless set).
"""

from collections import Counter

from django.core.management.base import BaseCommand

from schools.estimates import POLLUTANTS, SensorData, estimate_method, estimate_school
from schools.models import School

NAMES = {'no2': 'NO2', 'pm25': 'PM2.5', 'pm10': 'PM10'}


class Command(BaseCommand):
    help = 'Compare the latest figures from both estimating methods, pollutant by pollutant'

    def add_arguments(self, parser):
        parser.add_argument('--school', help='Only schools whose name contains this text')
        parser.add_argument('--summary-only', action='store_true', help='Skip the per-school lines')

    def handle(self, *args, **options):
        schools = School.objects.select_related('direct_sensor').order_by('name')
        if options['school']:
            schools = schools.filter(name__icontains=options['school'])
        schools = list(schools)
        if not schools:
            self.stdout.write('No schools found.')
            return

        data = SensorData.load(schools)
        self.stdout.write(f"Method shown in the app: {estimate_method()}\n")

        kinds = {p: Counter() for p in POLLUTANTS}
        confidence = {p: Counter() for p in POLLUTANTS}
        gaps = {p: [] for p in POLLUTANTS}  # (school, current - third)
        skipped = Counter()
        mixed = 0

        for school in schools:
            estimates = estimate_school(school, data)
            codes = {e['sensor_code'] for e in estimates.values() if e}
            if len(codes) > 1:
                mixed += 1
            if not options['summary_only']:
                self.stdout.write(self.style.MIGRATE_HEADING(school.name))

            for p in POLLUTANTS:
                e = estimates[p]
                if e is None:
                    kinds[p]['none'] += 1
                    if not options['summary_only']:
                        self.stdout.write(f'  {NAMES[p]:6} no sensor figure (LAEI 2022 only)')
                    continue

                kinds[p][e['kind']] += 1
                confidence[p][e['confidence']] += 1
                for s in e['skipped']:
                    skipped[s] += 1
                if e['current_method'] is not None and e['third_method'] is not None:
                    gaps[p].append((school.name, e['current_method'] - e['third_method']))

                if options['summary_only']:
                    continue
                ratio = e['compared_with_average']
                ratio = f'{ratio:.2f}x avg' if ratio is not None else 'no avg'
                sensor = (f"{e['sensor_code']} {e['sensor_site_type'].lower()}, "
                          f"{e['sensor_distance']:.0f} m" if e['sensor_distance'] is not None
                          else e['sensor_code'])
                when = e['reading_timestamp'].strftime('%a %H:%M')
                line = f"  {NAMES[p]:6} {e['kind']:9} {e['value']:6.1f}  {sensor}, {ratio}, {e['confidence']}, {when}"
                if e['kind'] == 'estimated':
                    third = e['third_method']
                    third = f'{third:.1f}' if third is not None else 'n/a (no LAEI at sensor)'
                    line += f"  [current {e['current_method']:.1f} | third {third}]"
                if e['skipped']:
                    line += f"  skipped: {', '.join(e['skipped'])}"
                self.stdout.write(line)

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING(f'\nSummary for {len(schools)} schools'))
        for p in POLLUTANTS:
            k = kinds[p]
            self.stdout.write(
                f"  {NAMES[p]:6} measured {k['measured']:3}, estimated {k['estimated']:3}, "
                f"LAEI only {k['none']:3}   confidence: "
                + ', '.join(f'{c} {n}' for c, n in confidence[p].most_common())
            )
        self.stdout.write(f'  Schools using more than one sensor across pollutants: {mixed}')

        self.stdout.write(self.style.MIGRATE_HEADING('\nCurrent minus third method (µg/m³)'))
        for p in POLLUTANTS:
            diffs = sorted(d for _, d in gaps[p])
            if not diffs:
                self.stdout.write(f'  {NAMES[p]:6} no estimates to compare')
                continue
            median = diffs[len(diffs) // 2]
            widest = max(gaps[p], key=lambda g: abs(g[1]))
            self.stdout.write(
                f'  {NAMES[p]:6} {len(diffs)} schools, median {median:+.1f}, '
                f'range {diffs[0]:+.1f} to {diffs[-1]:+.1f}; widest: {widest[0]} ({widest[1]:+.1f})'
            )

        if skipped:
            self.stdout.write(self.style.WARNING('\nSensors skipped as possibly faulty'))
            for s, n in skipped.most_common():
                self.stdout.write(f'  {s}: {n} school-pollutant(s)')