"""
Fetch 12-month averages for Breathe London sensors.

Breathe London restarted with new devices in spring 2025, so a calendar
year doesn't work yet. This averages the last 12 full months instead
(run in November 2026, that's November 2025 to October 2026).

Each result is saved as SensorAnnualStats with:
    year         = the year the period ends in (so it counts as the latest)
    period_start = first day of the period
    period_end   = last day of the period

Breathe sensors measure NO2 and PM2.5 only (no PM10 or O3).

Usage:
    python manage.py fetch_breathe_annual_stats --dry-run
    python manage.py fetch_breathe_annual_stats --sensor=BL0084 --dry-run
    python manage.py fetch_breathe_annual_stats
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.management.base import BaseCommand

from air_quality.models import Sensor, SensorAnnualStats
from air_quality.services.breathe_london_api import BreatheLondonApi


def last_12_full_months(now):
    """
    Return (start, end) for the 12 complete months before `now`.
    `end` is not included: (1 Nov 2025, 1 Nov 2026) = Nov 2025 to Oct 2026.
    """
    end = datetime(now.year, now.month, 1, tzinfo=dt_timezone.utc)
    start = end.replace(year=end.year - 1)
    return start, end


class Command(BaseCommand):
    help = 'Fetch 12-month averages for Breathe London sensors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sensor',
            type=str,
            help='Fetch for one site_code only',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show the averages without saving them',
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, 'BREATHE_LONDON_API_KEY', None)
        if not api_key:
            self.stderr.write(self.style.ERROR('BREATHE_LONDON_API_KEY not found in settings'))
            return

        api = BreatheLondonApi(api_key)
        dry_run = options['dry_run']

        start, end = last_12_full_months(datetime.now(dt_timezone.utc))
        last_day = (end - timedelta(days=1)).date()

        sensors = Sensor.objects.filter(network='BREATHE', is_active=True)
        if options['sensor']:
            sensors = sensors.filter(site_code=options['sensor'])

        if not sensors.exists():
            self.stdout.write(self.style.WARNING('No active Breathe London sensors found.'))
            return

        self.stdout.write(f'Period:  {start.date()} to {last_day}')
        self.stdout.write(f'Sensors: {sensors.count()} (12 requests each, so this takes a while)')
        if dry_run:
            self.stdout.write(self.style.WARNING('** DRY RUN - nothing will be saved **'))
        self.stdout.write('')

        saved = 0
        skipped = 0
        errors = 0

        for sensor in sensors:
            try:
                means = api.get_period_means(sensor.site_code, start, end)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  {sensor.site_code}: error - {str(e)[:60]}'))
                errors += 1
                continue

            no2 = means.get('no2')
            pm25 = means.get('pm25')
            capture = means.get('capture', {})
            capture_text = ', '.join(
                f'{name} {share:.1%}' for name, share in sorted(capture.items())
            ) or 'no data'

            # If neither pollutant passes the 75% rule
            if no2 is None and pm25 is None:
                self.stdout.write(
                    self.style.WARNING(f'  {sensor.site_code}: skipped (capture: {capture_text})')
                )
                skipped += 1
                continue

            values = []
            if no2 is not None:
                values.append(f'NO₂={no2:.1f}')
            if pm25 is not None:
                values.append(f'PM2.5={pm25:.1f}')

            self.stdout.write(
                f'  {sensor.site_code} ({sensor.name[:28]}): '
                f'{", ".join(values)} µg/m³ (capture: {capture_text})'
            )

            if dry_run:
                continue

            # capture_rate holds one number, so store the lower of the
            # pollutants that were saved, as a percentage.
            saved_captures = [capture[name] for name in ('no2', 'pm25') if means.get(name) is not None]
            capture_rate = round(min(saved_captures) * 100, 1)

            SensorAnnualStats.objects.update_or_create(
                sensor=sensor,
                year=last_day.year,
                defaults={
                    'no2_mean': no2,
                    'pm25_mean': pm25,
                    'pm10_mean': None,
                    'o3_mean': None,
                    'capture_rate': capture_rate,
                    'period_start': start.date(),
                    'period_end': last_day,
                },
            )
            saved += 1

        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write(f'  Saved:   {saved}')
        self.stdout.write(f'  Skipped: {skipped}')
        self.stdout.write(f'  Errors:  {errors}')
        if dry_run:
            self.stdout.write(self.style.WARNING('** DRY RUN - nothing saved **'))
