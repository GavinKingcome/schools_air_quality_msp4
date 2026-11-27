"""
Latest-reading estimates for schools, pollutant by pollutant.

For each pollutant (NO2, PM2.5, PM10) separately:

1. A direct school uses its own sensor's value from the last 48 hours,
   marked "measured".
2. Otherwise, go down the school's ranked sensor list (SchoolSensor) and
   use the first sensor that has a value for this pollutant from the last
   48 hours and a yearly average for it, and whose reading isn't wildly
   off that average (below 0.2 or above 5 times suggests a fault, so
   that sensor is skipped and the next one tried).
3. Work out both estimates; settings.ESTIMATE_METHOD chooses which is shown:
     'current': LAEI at the school x (reading now / sensor's yearly average)
     'third':   reading now x (LAEI at the school / LAEI at the sensor),
                using the 100 m area median for urban background sensors
                and the sensor's own 20 m cell for others
4. Confidence for that pollutant, by setting match and distance (agreed
   25 November 2026): measured at the school = high (reference) or
   medium-high (Breathe); urban background under 1 km = medium;
   urban background 1 to 2 km = medium-low; roadside or other = low.

5. Alongside the latest hour, a 24-hour average from the same sensor (the
   24 hours up to that reading), worked out the same way, and only when at
   least 18 of the 24 hours have a value. It's compared with the WHO's
   24-hour guideline, which only applies to 24-hour averages.

SensorData.load() fetches everything for many schools in a few queries,
so the map doesn't query the database once per school and pollutant.
"""

from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from air_quality.models import Reading, SensorAnnualStats

POLLUTANTS = ('no2', 'pm25', 'pm10')

# The school's LAEI 2022 annual average for each pollutant
SCHOOL_LAEI_FIELDS = {'no2': 'no2_2022', 'pm25': 'pm25_2022', 'pm10': 'pm10_mean_2022'}

# A reading counts as current if it's no more than this old
FRESH_HOURS = 48

# The 24-hour average needs at least this many of the 24 hours
DAY_HOURS = 24
DAY_MIN_HOURS = 18

# Reading ÷ yearly average outside this range suggests a sensor fault
FAULT_LOW, FAULT_HIGH = 0.2, 5.0


def estimate_method():
    """'current' (the default until the validation test decides) or 'third'."""
    return getattr(settings, 'ESTIMATE_METHOD', 'current')


class SensorData:
    """Everything the estimates need, loaded once for a set of schools."""

    def __init__(self, latest, averages, lists, series=None):
        self.latest = latest      # {sensor_id: {pollutant: (value, timestamp)}}
        self.averages = averages  # {sensor_id: {pollutant: yearly average}}
        self.lists = lists        # {school_id: [SchoolSensor, ...]} in rank order
        self.series = series or {}  # {sensor_id: {pollutant: [(timestamp, value), ...]}}, newest first

    def day_average(self, sensor_id, pollutant, end):
        """
        The sensor's average over the 24 hours up to and including `end`,
        as (average, hours with a value), or (None, hours) if fewer than
        DAY_MIN_HOURS have a value.
        """
        start = end - timedelta(hours=DAY_HOURS)
        values = [v for t, v in self.series.get(sensor_id, {}).get(pollutant, [])
                  if start < t <= end]
        if len(values) < DAY_MIN_HOURS:
            return None, len(values)
        return sum(values) / len(values), len(values)

    @classmethod
    def load(cls, schools):
        from schools.models import SchoolSensor  # imported here to avoid a circular import

        schools = list(schools)
        entries = list(
            SchoolSensor.objects.filter(school_id__in=[s.id for s in schools])
            .select_related('sensor')
            .order_by('school_id', 'rank')
        )
        lists = defaultdict(list)
        for entry in entries:
            lists[entry.school_id].append(entry)

        sensor_ids = {e.sensor_id for e in entries}
        sensor_ids |= {s.direct_sensor_id for s in schools if s.direct_sensor_id}

        # Each sensor's hourly values for the last 48 + 24 hours: enough for the
        # latest value (up to 48 hours old) and the 24 hours before it.
        now = timezone.now()
        fresh_since = now - timedelta(hours=FRESH_HOURS)
        since = fresh_since - timedelta(hours=DAY_HOURS)
        latest = defaultdict(dict)
        series = defaultdict(lambda: defaultdict(list))
        readings = (
            Reading.objects.filter(sensor_id__in=sensor_ids, timestamp__gte=since)
            .order_by('sensor_id', '-timestamp')
            .values('sensor_id', 'timestamp', *POLLUTANTS)
        )
        for r in readings:
            found = latest[r['sensor_id']]
            for p in POLLUTANTS:
                if r[p] is None:
                    continue
                series[r['sensor_id']][p].append((r['timestamp'], r[p]))
                # Per pollutant: a latest hour with PM2.5 but no NO2 can still supply PM2.5
                if p not in found and r['timestamp'] >= fresh_since:
                    found[p] = (r[p], r['timestamp'])

        # Each sensor's most recent yearly averages
        averages = {}
        stats = SensorAnnualStats.objects.filter(sensor_id__in=sensor_ids).order_by('sensor_id', '-year')
        for a in stats:
            if a.sensor_id not in averages:
                averages[a.sensor_id] = {'no2': a.no2_mean, 'pm25': a.pm25_mean, 'pm10': a.pm10_mean}

        return cls(dict(latest), averages, dict(lists), {k: dict(v) for k, v in series.items()})


def sensor_laei(sensor, pollutant):
    """
    LAEI 2022 at the sensor, for the third method: the 100 m area median
    for an urban background sensor (a road strip in its own cell barely
    counts), otherwise its own 20 m cell (for a roadside sensor, the road
    is what it measures).
    """
    own = getattr(sensor, f'laei_{pollutant}_2022', None)
    area = getattr(sensor, f'laei_{pollutant}_2022_area', None)
    if sensor.site_type == 'urban_background' and area:
        return area
    return own


def confidence_for(sensor, distance, measured):
    """Confidence by setting match and distance; the network only matters when measured."""
    if measured:
        return 'high' if sensor.is_reference_grade else 'medium-high'
    if sensor.site_type != 'urban_background':
        return 'low'
    return 'medium' if distance is not None and distance < 1000 else 'medium-low'


def describe_sensor(sensor, distance):
    """The sensor fields the map and school page already use."""
    return {
        'sensor_code': sensor.site_code,
        'sensor_network': sensor.get_network_display(),
        'sensor_site_type': sensor.get_site_type_display(),
        'sensor_is_reference': sensor.is_reference_grade,
        'sensor_distance': float(distance) if distance is not None else None,
    }


def day_fields(pollutant, day, hours):
    """The 24-hour average and how it compares with the WHO's 24-hour guideline."""
    from schools.models import DAILY_GUIDELINES  # imported here to avoid a circular import
    guideline = DAILY_GUIDELINES[pollutant]
    return {
        'day_average': round(day, 1) if day is not None else None,
        'day_hours': hours,
        'day_guideline': guideline,
        'day_within_guideline': (day <= guideline) if day is not None else None,
    }


def estimate_pollutant(school, pollutant, data, method=None):
    """
    The latest figure for one pollutant at one school, or None.

    Returns a dict: value, kind ('measured' or 'estimated'), the sensor
    used, reading_timestamp, compared_with_average (reading ÷ the sensor's
    yearly average), confidence, both estimates (current_method,
    third_method) for checking and the validation test, and skipped
    (sensors passed over because their reading looked faulty).
    A direct sensor with a faulty-looking reading is skipped too, and the
    school falls back to its list.
    """
    method = method or estimate_method()
    skipped = []  # sensors passed over because their reading looked faulty

    # 1. Measured at the school
    if school.direct_sensor_id:
        found = data.latest.get(school.direct_sensor_id, {}).get(pollutant)
        if found:
            value, timestamp = found
            average = data.averages.get(school.direct_sensor_id, {}).get(pollutant)
            factor = value / average if average and average > 0 else None
            sensor = school.direct_sensor
            if factor is not None and not FAULT_LOW <= factor <= FAULT_HIGH:
                skipped.append(f'{sensor.site_code} ({factor:.2f} x its yearly average)')
            else:
                distance = school.direct_sensor_distance
                day, day_hours = data.day_average(school.direct_sensor_id, pollutant, timestamp)
                return {
                    'value': round(value, 1),
                    **day_fields(pollutant, day, day_hours),
                    'kind': 'measured',
                    **describe_sensor(sensor, distance),
                    'reading_timestamp': timestamp,
                    'compared_with_average': round(factor, 3) if factor is not None else None,
                    'confidence': confidence_for(sensor, distance, measured=True),
                    'current_method': None,
                    'third_method': None,
                    'method_used': 'measured',
                    'skipped': skipped,
                    'workings': None,
                }

    # 2. Estimated from the first suitable sensor on the school's list
    baseline = getattr(school, SCHOOL_LAEI_FIELDS[pollutant])
    if baseline is None:
        return None
    baseline = float(baseline)

    for entry in data.lists.get(school.id, []):
        sensor = entry.sensor
        found = data.latest.get(sensor.id, {}).get(pollutant)
        average = data.averages.get(sensor.id, {}).get(pollutant)
        if not found or not average or average <= 0:
            continue
        value, timestamp = found
        factor = value / average
        if not FAULT_LOW <= factor <= FAULT_HIGH:
            # Looks like a sensor fault: note it and try the next sensor
            skipped.append(f'{sensor.site_code} ({factor:.2f} x its yearly average)')
            continue

        current = baseline * factor
        at_sensor = sensor_laei(sensor, pollutant)
        third = value * baseline / at_sensor if at_sensor else None
        # The third method needs LAEI at the sensor; without it, fall back to the current method
        used = 'third' if (method == 'third' and third is not None) else 'current'
        shown = third if used == 'third' else current

        # The 24 hours up to this reading, scaled to the school the same way
        sensor_day, day_hours = data.day_average(sensor.id, pollutant, timestamp)
        day = None
        if sensor_day is not None:
            day = sensor_day * baseline / at_sensor if used == 'third' else baseline * sensor_day / average

        return {
            'value': round(shown, 1),
            **day_fields(pollutant, day, day_hours),
            'kind': 'estimated',
            **describe_sensor(sensor, entry.distance_m),
            'reading_timestamp': timestamp,
            'compared_with_average': round(factor, 3),
            'confidence': confidence_for(sensor, entry.distance_m, measured=False),
            'current_method': round(current, 1),
            'third_method': round(third, 1) if third is not None else None,
            'method_used': used,
            'skipped': skipped,
            # The numbers behind the estimate, for "How is this worked out?"
            'workings': {
                'sensor_value': round(value, 1),
                'sensor_day_average': round(sensor_day, 1) if sensor_day is not None else None,
                'sensor_average': round(average, 1),
                'laei_school': round(baseline, 2),
                'laei_sensor': round(at_sensor, 2) if at_sensor else None,
                # 'area' = median of the 100 m around the sensor; 'spot' = its own 20 m square
                'laei_sensor_kind': 'area' if (sensor.site_type == 'urban_background'
                                               and getattr(sensor, f'laei_{pollutant}_2022_area', None))
                                    else 'spot',
            },
        }

    return None


def explain(e, name):
    """
    "How is this worked out?" for one estimated pollutant, in plain words
    with the school's own numbers. None for a measurement.
    The map popup builds the same text in JavaScript; change both together.
    """
    w = e.get('workings')
    if not w:
        return None
    where = 'around the sensor' if w['laei_sensor_kind'] == 'area' else "at the sensor's spot"
    code = e['sensor_code']
    if e['method_used'] == 'third':
        text = (f"{code} measured {w['sensor_value']:.1f} µg/m³ of {name}. The pollution map "
                f"(LAEI 2022) gives a yearly average of {w['laei_school']:.2f} at the school and "
                f"{w['laei_sensor']:.2f} {where}. So the estimate for the school is "
                f"{w['sensor_value']:.1f} × {w['laei_school']:.2f} ÷ {w['laei_sensor']:.2f} = {e['value']:.1f} µg/m³.")
    else:
        text = (f"{code} measured {w['sensor_value']:.1f} µg/m³ of {name}, against its yearly "
                f"average of {w['sensor_average']:.1f}. The pollution map (LAEI 2022) gives the "
                f"school a yearly average of {w['laei_school']:.2f}. So the estimate for the school is "
                f"{w['laei_school']:.2f} × {w['sensor_value']:.1f} ÷ {w['sensor_average']:.1f} = {e['value']:.1f} µg/m³.")
    if e.get('day_average') is not None:
        text += " The 24-hour figure is worked out the same way, from the sensor's 24-hour average."
    return text


def estimate_school(school, data, method=None):
    """{pollutant: estimate or None} for one school."""
    return {p: estimate_pollutant(school, p, data, method) for p in POLLUTANTS}