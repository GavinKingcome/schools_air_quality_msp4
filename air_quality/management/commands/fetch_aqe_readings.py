"""
Django management command to fetch Air Quality England (AQE) readings.

The Ricardo files are updated once a day and hold a whole year per site,
so the default window is 48 hours rather than 2. Each run downloads the
current year's file for each active AQE sensor and keeps the recent rows.

Usage:
    python manage.py fetch_aqe_readings               # last 48 hours
    python manage.py fetch_aqe_readings --hours=168   # last week
    python manage.py fetch_aqe_readings --year=2024   # backfill a whole year
    python manage.py fetch_aqe_readings --sensor=SWK12 --year=2025
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from air_quality.models import Sensor, Reading
from air_quality.services.aqe_api import AQEApi, POLLUTANT_MAP
from datetime import timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def clean(value):
    """NaN -> None, otherwise float."""
    if value is None or pd.isna(value):
        return None
    return float(value)


class Command(BaseCommand):
    help = 'Fetch readings from Air Quality England sensors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=48,
            help='Hours of data to keep from the downloaded file (default: 48)',
        )
        parser.add_argument(
            '--year',
            action='append',
            type=int,
            help='Backfill: load the whole of this year (can be given more than once)',
        )
        parser.add_argument(
            '--sensor',
            type=str,
            help='Fetch for a specific site_code only',
        )

    def handle(self, *args, **options):
        api = AQEApi()
        hours = options['hours']
        backfill_years = options.get('year')

        sensors = Sensor.objects.filter(network='AQE', is_active=True)
        if options['sensor']:
            # Allow closed sensors when a specific code is asked for (history)
            sensors = Sensor.objects.filter(network='AQE', site_code=options['sensor'])

        if not sensors.exists():
            self.stdout.write('No AQE sensors found. Run sync_aqe_sensors first.')
            return

        now = timezone.now()

        if backfill_years:
            years = sorted(set(backfill_years))
            cutoff = None
            self.stdout.write(f'Backfilling {sensors.count()} AQE sensors for {years}')
        else:
            cutoff = now - timedelta(hours=hours)
            years = sorted({cutoff.year, now.year})
            self.stdout.write(
                f'Fetching readings for {sensors.count()} AQE sensors (last {hours} hours)...'
            )

        readings_created = 0
        readings_updated = 0
        sensors_no_data = 0
        errors = 0

        for sensor in sensors:
            try:
                frames = []
                for year in years:
                    df = api.get_hourly(sensor.site_code, year)
                    if df is not None:
                        frames.append(df)

                if not frames:
                    sensors_no_data += 1
                    continue

                df = pd.concat(frames, ignore_index=True)
                if cutoff is not None:
                    df = df[df['date'] >= cutoff]

                value_cols = [c for c in POLLUTANT_MAP.values() if c in df.columns]

                for row in df.itertuples(index=False):
                    values = {col: clean(getattr(row, col)) for col in value_cols}
                    if not any(v is not None for v in values.values()):
                        continue  # nothing measured this hour

                    reading, created = Reading.objects.update_or_create(
                        sensor=sensor,
                        timestamp=row.date.to_pydatetime(),
                        defaults={
                            'no2': values.get('no2'),
                            'pm25': values.get('pm25'),
                            'pm10': values.get('pm10'),
                            'o3': values.get('o3'),
                            'nox': values.get('nox'),
                        },
                    )
                    if created:
                        readings_created += 1
                    else:
                        readings_updated += 1

                self.stdout.write(f'  {sensor.site_code}: {len(df)} rows processed')

            except Exception as e:
                logger.error(f'Error fetching AQE {sensor.site_code}: {e}')
                self.stdout.write(self.style.ERROR(f'  {sensor.site_code}: {str(e)[:60]}'))
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'\nFetch complete: {readings_created} created, {readings_updated} updated '
                f'({sensors_no_data} no data, {errors} errors)'
            )
        )
