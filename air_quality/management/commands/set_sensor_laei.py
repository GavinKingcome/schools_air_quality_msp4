"""
Look up LAEI 2022 annual averages at each sensor's location.

Reads the LAEI 2022 ASCII grids (20 m cells, British National Grid) and
saves the NO2, PM2.5 and PM10 values on each Sensor, using the same
lookup as the schools' values: the 20 m cell that contains the point.

These values are needed for the third method
(sensor now x LAEI at the school / LAEI at the sensor) and for the
LAEI similarity check.

--check-schools=N also looks up N random schools the same way and compares
the results with their stored values, to confirm the two lookups match.

Usage:
    python manage.py set_sensor_laei --check-schools=15 --dry-run
    python manage.py set_sensor_laei
    python manage.py set_sensor_laei --laei-dir=/path/to/LAEI/ASCII
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pyproj import Transformer

from air_quality.models import Sensor
from schools.models import School

# pollutant: (grid file, Sensor field, School field)
GRIDS = {
    'no2': ('LAEI2022_V1_NO2.asc', 'laei_no2_2022', 'no2_2022'),
    'pm25': ('LAEI2022_V1_PM25.asc', 'laei_pm25_2022', 'pm25_2022'),
    'pm10': ('LAEI2022_V1_PM10m.asc', 'laei_pm10_2022', 'pm10_mean_2022'),
}

# Latitude/longitude (WGS84) to British National Grid, in metres
TO_BNG = Transformer.from_crs('EPSG:4326', 'EPSG:27700', always_xy=True)


def to_bng(latitude, longitude):
    easting, northing = TO_BNG.transform(float(longitude), float(latitude))
    return easting, northing


def lookup(path, points):
    """
    Values at many points from one ESRI ASCII grid, reading only the rows needed.

    points: {key: (easting, northing)}
    Returns {key: value rounded to 2 decimal places, or None if outside the
    grid or no data}.
    """
    results = {key: None for key in points}
    with open(path) as f:
        header = {}
        for _ in range(6):
            name, value = f.readline().split()
            header[name.lower()] = float(value)

        ncols, nrows = int(header['ncols']), int(header['nrows'])
        size = header['cellsize']
        nodata = header.get('nodata_value', -9999)
        # The grid's lower-left corner (some files give the centre of that cell)
        x0 = header['xllcorner'] if 'xllcorner' in header else header['xllcenter'] - size / 2
        y0 = header['yllcorner'] if 'yllcorner' in header else header['yllcenter'] - size / 2

        # Which row and column each point falls in. Rows in the file run
        # from north (row 0) to south, so count down from the top.
        wanted = {}
        for key, (easting, northing) in points.items():
            col = int((easting - x0) // size)
            row = nrows - 1 - int((northing - y0) // size)
            if 0 <= col < ncols and 0 <= row < nrows:
                wanted.setdefault(row, []).append((key, col))

        last_row = max(wanted) if wanted else -1
        for row, line in enumerate(f):
            if row > last_row:
                break
            if row in wanted:
                values = line.split()
                for key, col in wanted[row]:
                    value = float(values[col])
                    results[key] = None if value == nodata or value < 0 else round(value, 2)
    return results


class Command(BaseCommand):
    help = 'Look up LAEI 2022 annual averages at each sensor location'

    def add_arguments(self, parser):
        parser.add_argument(
            '--laei-dir',
            default=str(Path(settings.BASE_DIR) / 'LAEI' / 'ASCII'),
            help='Folder holding the LAEI 2022 .asc grids (default: LAEI/ASCII in the project)'
        )
        parser.add_argument(
            '--check-schools',
            type=int,
            default=0,
            help='Also look up this many random schools and compare with their stored values'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show the values without saving'
        )

    def handle(self, *args, **options):
        laei_dir = Path(options['laei_dir'])
        for filename, _, _ in GRIDS.values():
            if not (laei_dir / filename).exists():
                raise CommandError(f'Missing LAEI grid: {laei_dir / filename}')

        sensors = list(Sensor.objects.all())
        points = {('sensor', s.id): to_bng(s.latitude, s.longitude) for s in sensors}

        check = []
        if options['check_schools']:
            check = list(
                School.objects.exclude(latitude=None).exclude(no2_2022=None)
                .order_by('?')[:options['check_schools']]
            )
            points.update({('school', s.id): to_bng(s.latitude, s.longitude) for s in check})

        values = {}
        for pollutant, (filename, _, _) in GRIDS.items():
            self.stdout.write(f'Reading {filename}...')
            values[pollutant] = lookup(laei_dir / filename, points)

        # === CHECK AGAINST THE SCHOOLS' STORED VALUES ===
        if check:
            self.stdout.write('\nCheck: the same lookup for schools, against their stored values')
            matches = 0
            for school in check:
                key = ('school', school.id)
                parts, all_match = [], True
                for pollutant, (_, _, school_field) in GRIDS.items():
                    stored = getattr(school, school_field)
                    stored = float(stored) if stored is not None else None
                    found = values[pollutant][key]
                    same = (stored == found) if (stored is None or found is None) else abs(stored - found) < 0.01
                    all_match = all_match and same
                    parts.append(f'{pollutant} {stored} / {found}')
                matches += all_match
                mark = '✓' if all_match else '✗'
                self.stdout.write(f'  {mark} {school.name[:34]:<34} ' + ' | '.join(parts))
            self.stdout.write(f'  {matches} of {len(check)} schools match (stored / looked up)')

        # === SAVE ON EACH SENSOR ===
        missing = []
        for sensor in sensors:
            key = ('sensor', sensor.id)
            for pollutant, (_, sensor_field, _) in GRIDS.items():
                setattr(sensor, sensor_field, values[pollutant][key])
            if sensor.laei_no2_2022 is None:
                missing.append(sensor.site_code)

        if not options['dry_run']:
            Sensor.objects.bulk_update(sensors, [field for _, field, _ in GRIDS.values()])

        # === SUMMARY ===
        self.stdout.write('\nActive sensors (LAEI 2022 at the sensor, µg/m³):')
        for sensor in sorted((s for s in sensors if s.is_active), key=lambda s: (s.network, s.site_code)):
            self.stdout.write(
                f'  {sensor.network:8} {sensor.site_code:8} {sensor.get_site_type_display():17} '
                f'NO2 {sensor.laei_no2_2022}  PM2.5 {sensor.laei_pm25_2022}  PM10 {sensor.laei_pm10_2022}'
            )
        self.stdout.write(f'\n{len(sensors)} sensors looked up; {len(missing)} outside the grid or without data'
                          + (f': {", ".join(missing)}' if missing else ''))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('** DRY RUN - nothing saved **'))
        else:
            self.stdout.write(self.style.SUCCESS('Saved.'))