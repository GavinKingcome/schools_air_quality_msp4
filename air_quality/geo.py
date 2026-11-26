"""
Shared distance helpers for the sensor commands.

All distances are straight-line distances over the earth's surface
(the haversine formula), in metres.
"""

from math import radians, sin, cos, sqrt, atan2

# Every sensor in these boroughs is synced, open or closed
HOME_BOROUGHS = {'lambeth', 'southwark'}

# Outside the home boroughs, a sensor is synced only if it's open and
# this close to at least one school. Matches assign_sensors' default
# --reference-threshold: a sensor further away is never used.
NEARBY_METRES = 2000


def haversine_distance(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points, in metres."""
    R = 6371000  # Earth's radius in metres

    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def school_locations():
    """Every school's (latitude, longitude), loaded once."""
    from schools.models import School  # imported here to keep the apps loosely linked
    return [
        (float(s.latitude), float(s.longitude))
        for s in School.objects.exclude(latitude=None).exclude(longitude=None)
    ]


def near_any_school(lat, lon, schools, max_metres=NEARBY_METRES):
    """True if the point is within max_metres of at least one school."""
    return any(
        haversine_distance(lat, lon, s_lat, s_lon) <= max_metres
        for s_lat, s_lon in schools
    )