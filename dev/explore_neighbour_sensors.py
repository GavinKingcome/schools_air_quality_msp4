"""
One-off check (21 Nov 2026): which sensors, in any borough, are within
2 km of one of our schools? Reads the APIs only; saves nothing.

Run: python manage.py shell < dev/explore_neighbour_sensors.py
"""
import math
from collections import Counter
from django.conf import settings
from schools.models import School
from air_quality.models import Sensor
from air_quality.services.laqn_api import LAQNApi
from air_quality.services.breathe_london_api import BreatheLondonApi

MAX_M = 2000
NEIGHBOURS = ['Wandsworth', 'Merton', 'Croydon', 'Bromley', 'Lewisham',
              'Westminster', 'City of London', 'Tower Hamlets']


def metres(lat1, lon1, lat2, lon2):
    """Distance between two points on the earth's surface, in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(a))


schools = [(s.name, float(s.latitude), float(s.longitude)) for s in School.objects.all()]
existing = set(Sensor.objects.values_list('site_code', flat=True))


def nearest_school(lat, lon):
    return min((metres(lat, lon, la, lo), name) for name, la, lo in schools)


def report(title, rows):
    rows.sort(key=lambda r: r[4])
    print(f'\n{title}: {len(rows)} open sites within 2 km of a school')
    for code, name, borough, kind, dist, school in rows:
        flag = '' if code in existing else '  NEW'
        print(f'  {code:8} {borough[:14]:14} {kind[:17]:17} {dist:5.0f} m  {school[:32]}{flag}')
    print('  New, by borough:', dict(Counter(r[2] for r in rows if r[0] not in existing)))


# LAQN: one call returns every London site
rows = []
for s in LAQNApi().get_monitoring_sites():
    if s.get('@DateClosed'):
        continue
    try:
        lat, lon = float(s['@Latitude']), float(s['@Longitude'])
    except (KeyError, TypeError, ValueError):
        continue
    dist, school = nearest_school(lat, lon)
    if dist <= MAX_M:
        rows.append((s.get('@SiteCode'), s.get('@SiteName', ''), s.get('@LocalAuthorityName', ''),
                     s.get('@SiteType', ''), dist, school))
report('LAQN', rows)

# Breathe London: try every sensor at once, else borough by borough
api = BreatheLondonApi(settings.BREATHE_LONDON_API_KEY)
try:
    breathe = api._make_request('ListSensors')
except Exception as e:
    breathe = None
    print('\nBreathe: asking without a borough failed:', e)
if isinstance(breathe, list):
    print(f'\nBreathe: one call returned {len(breathe)} installations (all boroughs)')
else:
    breathe = api.get_sensors_by_borough(['Lambeth', 'Southwark'] + NEIGHBOURS)
    print(f'\nBreathe: asked borough by borough, {len(breathe)} installations')

running = {s['SiteCode']: s for s in breathe if s.get('SiteCode') and s.get('EndDate') is None}
rows = []
for code, s in running.items():
    try:
        lat, lon = float(s['Latitude']), float(s['Longitude'])
    except (KeyError, TypeError, ValueError):
        continue
    dist, school = nearest_school(lat, lon)
    if dist <= MAX_M:
        rows.append((code, s.get('SiteName', ''), s.get('Borough') or '',
                     s.get('SiteClassification') or '', dist, school))
report('Breathe London', rows)