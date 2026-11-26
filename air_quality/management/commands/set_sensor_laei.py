"""
Look up LAEI 2022 annual averages at each sensor's location.

Reads the LAEI 2022 ASCII grids (20 m cells, British National Grid) and
saves two values per pollutant on each Sensor:

  - its own cell: the 20 m cell the sensor falls in, the same lookup as
    the schools' values (laei_no2_2022 etc.)
  - its area: the median of the 5 x 5 cells around it, about 100 m across
    (laei_no2_2022_area etc.). A road strip running through the sensor's
    own cell barely moves the median, so this describes the air around an
    urban background sensor more fairly (see BL0084, 25 November 2026).

These values are needed for the third method
(sensor now x LAEI at the school / LAEI at the sensor) and for the
LAEI similarity check.

--check-schools=N also looks up N random schools the same way and compares
their own cell with their stored values, to confirm the two lookups match.

Usage:
    python manage.py set_sensor_laei --check-schools=15 --dry-run
    python manage.py set_sensor_laei
    python manage.py set_sensor_laei --laei-dir=/path/to/LAEI/ASCII
"""

from pathlib import Path
import statistics

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pyproj import Transformer

from air_quality.models import Sensor
from schools.models import School

# pollutant: (grid file, Sensor field for its own cell, Sensor field for its area, School field)
GRIDS = {
    'no2': ('LAEI2022_V1_NO2.asc', 'laei_no2_2022', 'laei_no2_2022_area', 'no2_2022'),
    'pm25': ('LAEI2022_V1_PM25.asc', 'laei_pm25_2022', 'laei_pm25_2022_area', 'pm25_2022'),
    'pm10': ('LAEI2022_V1_PM10m.asc', 'laei_pm10_2022', 'laei_pm10_2022_area', 'pm10_mean_2022'),
}

# Cells either side of the sensor's own cell for the area median:
# 2 gives a 5 x 5 block, about 100 m across
AREA_RADIUS = 2

# Flag an urban background sensor whose own cell is this much above its area
FLAG_ABOVE_AREA = 1.2

# Latitude/longitude (WGS84) to British National Grid, in metres
TO_BNG = Transformer.from_crs('EPSG:4326', 'EPSG:27700', always_xy=True)


def to_bng(latitude, longitude):
    easting, northing = TO_BNG.transform(float(longitude), float(latitude))
    return easting, northing


def lookup(path, points, radius=AREA_RADIUS):
    """
    Values at many points from one ESRI ASCII grid, reading only the rows needed.

    points: {key: (easting, northing)}
    Returns {key: (own cell, area median)}, each rounded to 2 decimal places,
    or None if outside the grid or no data.
    """
    results = {key: (None, None) for key in points}
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
        centres = {}
        wanted_rows = set()
        for key, (easting, northing) in points.items():
            col = int((easting - x0) // size)
            row = nrows - 1 - int((northing - y0) // size)
            if 0 <= col < ncols and 0 <= row < nrows:
                centres[key] = (row, col)
                wanted_rows.update(range(row - radius, row + radius + 1))

        # Keep only the rows needed (each file is about 60 MB)
        rows = {}
        last_row = max(wanted_rows) if wanted_rows else -1
        for row, line in enumerate(f):
            if row > last_row:
                break
            if row in wanted_rows:
                rows[row] = line.split()

    def value_at(row, col):
        if row not in rows or not 0 <= col < ncols:
            return None
        value = float(rows[row][col])
        return None if value == nodata or value < 0 else value

    for key, (row, col) in centres.items():
        own = value_at(row, col)
        block = [
            value_at(r, c)
            for r in range(row - radius, row + radius + 1)
            for c in range(col - radius, col + radius + 1)
        ]
        block = [v for v in block if v is not None]
        area = statistics.median(block) if block else None
        results[key] = (
            round(own, 2) if own is not None else None,
            round(area, 2) if area is not None else None,
        )
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
        for filename, _, _, _ in GRIDS.values():
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
        for pollutant, (filename, _, _, _) in GRIDS.items():
            self.stdout.write(f'Reading {filename}...')
            values[pollutant] = lookup(laei_dir / filename, points)

        # === CHECK AGAINST THE SCHOOLS' STORED VALUES (own cell) ===
        if check:
            self.stdout.write('\nCheck: the same lookup for schools, against their stored values')
            matches = 0
            for school in check:
                key = ('school', school.id)
                parts, all_match = [], True
                for pollutant, (_, _, _, school_field) in GRIDS.items():
                    stored = getattr(school, school_field)
                    stored = float(stored) if stored is not None else None
                    found = values[pollutant][key][0]
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
            for pollutant, (_, own_field, area_field, _) in GRIDS.items():
                own, area = values[pollutant][key]
                setattr(sensor, own_field, own)
                setattr(sensor, area_field, area)
            if sensor.laei_no2_2022 is None:
                missing.append(sensor.site_code)

        if not options['dry_run']:
            fields = [f for _, own_field, area_field, _ in GRIDS.values() for f in (own_field, area_field)]
            Sensor.objects.bulk_update(sensors, fields)

        # === SUMMARY ===
        self.stdout.write('\nActive sensors: LAEI 2022 NO2 at the sensor, µg/m³ (own cell / 100 m area median)')
        flagged = []
        for sensor in sorted((s for s in sensors if s.is_active), key=lambda s: (s.network, s.site_code)):
            own, area = sensor.laei_no2_2022, sensor.laei_no2_2022_area
            flag = ''
            if (sensor.site_type == 'urban_background' and own and area
                    and own > area * FLAG_ABOVE_AREA):
                flag = '  <-- own cell well above its area'
                flagged.append(sensor.site_code)
            self.stdout.write(
                f'  {sensor.network:8} {sensor.site_code:8} {sensor.get_site_type_display():17} '
                f'{own} / {area}{flag}'
            )
        if flagged:
            self.stdout.write(
                f'\nUrban background sensors whose own cell is over {FLAG_ABOVE_AREA - 1:.0%} '
                f'above their area (probably a road strip in the cell): {", ".join(flagged)}'
            )
        self.stdout.write(f'\n{len(sensors)} sensors looked up; {len(missing)} outside the grid or without data'
                          + (f': {", ".join(missing)}' if missing else ''))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('** DRY RUN - nothing saved **'))
        else:
            self.stdout.write(self.style.SUCCESS('Saved.'))