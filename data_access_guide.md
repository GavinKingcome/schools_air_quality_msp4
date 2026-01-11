# Air Quality Data Access Guide for AirAware London

This guide covers how to access the three main data sources for your project: LAQN (reference monitors), Breathe London (low-cost sensors), and LAEI (modelled concentrations).

---

## 1. LAQN (London Air Quality Network)

**What it is:** Reference-grade continuous monitoring stations across London, managed by Imperial College London's Environmental Research Group.

**Data quality:** Highest accuracy - these are the "gold standard" measurements.

**Coverage:** ~150+ stations across London, but sparse coverage (stations are spread out).

### API Access

The LAQN API is free and open under the UK Open Government Licence.

**Base URL:** `https://api.erg.ic.ac.uk/AirQuality/`

**Key Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `/Information/MonitoringSites/GroupName=London/Json` | List all monitoring sites with coordinates |
| `/Information/MonitoringSiteSpecies/GroupName=London/Json` | Sites with pollutants measured |
| `/Hourly/MonitoringIndex/GroupName=London/Json` | Current hourly readings |
| `/Data/Site/SiteCode={code}/StartDate={date}/EndDate={date}/Json` | Historical data for a site |

**Example - Get all London sites:**
```python
import requests

url = "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json"
response = requests.get(url)
data = response.json()

# Each site has: @SiteCode, @SiteName, @Latitude, @Longitude, @SiteType, @LocalAuthorityName
sites = data['Sites']['Site']
for site in sites:
    print(f"{site['@SiteName']}: ({site.get('@Latitude')}, {site.get('@Longitude')})")
```

**Example - Get hourly data for a specific site:**
```python
url = "https://api.erg.ic.ac.uk/AirQuality/Data/Site/SiteCode=LB6/StartDate=2025-01-01/EndDate=2025-01-07/Json"
response = requests.get(url)
```

**Site types:**
- Roadside / Kerbside - near traffic
- Urban Background - representative of general urban exposure
- Suburban - lower density areas

### Lambeth & Southwark Sites

You'll want to filter the API response for:
- `@LocalAuthorityName == "Lambeth"` 
- `@LocalAuthorityName == "Southwark"`

Known key sites in these boroughs:
- **LB6** - Lambeth - Streatham Green (Urban Background) - 99% data capture
- **SK1** - Southwark - Old Kent Road (Roadside)
- **SK5** - Southwark - A2 (Roadside)

---

## 2. Breathe London

**What it is:** Network of ~600+ low-cost sensors (Airly sensors) across London, including many at schools and hospitals.

**Data quality:** Lower than LAQN but continuously calibrated against reference monitors.

**Coverage:** Much denser than LAQN - potentially sensors at or very near schools.

### API Access

Breathe London **requires registration** for API access.

**Register at:** https://www.breathelondon.org/developers

After registration, you receive an API key for accessing sensor data.

**Data license:** UK Open Government Licence v3.0 (requires attribution)

**Attribution required:** 
> "Contains Breathe London data licensed under the Open Government License v3.0"
> Link to: https://www.breathelondon.org/

### What sensors measure:
- NO₂ (nitrogen dioxide)
- PM2.5 (fine particulate matter)
- PM10 (coarse particulate matter)

### Alternative: Breathe London Pilot Data (Historical)

The original pilot scheme (2018-2021) data is available for direct download without registration:

**Website:** https://breathelondonpilot.org/

This includes 100 AQMesh pod locations from the pilot phase.

### Finding Sensors Near Schools

Once you have API access, you can query sensors by:
- `SiteLocationType` (Hospital, School, etc.)
- `OtherTags` (may include borough names like "Lambeth")
- `OrganisationName`

---

## 3. LAEI 2022 (London Atmospheric Emissions Inventory)

**What it is:** Modelled annual mean concentrations based on emissions inventory, traffic patterns, and meteorology.

**Data quality:** Validated against monitoring data; represents typical annual conditions.

**Resolution:** 20m grid across Greater London - every school will have a specific grid cell value.

**Limitation:** Static annual averages only - no real-time variation.

### Download Location

**London Datastore:** https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory-laei-2022-2lg5g/

### Available Files

| File Type | Description | Format |
|-----------|-------------|--------|
| Concentrations - ASCII | 20m grid concentrations | CSV/TXT |
| Concentrations - Excel | Same data in spreadsheet format | XLSX |
| Concentrations - GIS | Shapefiles for mapping | ESRI SHP |
| Grid Emissions Summary | 1km grid emissions by source | Excel/GIS |

### Concentration Data Fields

For each 20m grid cell:
- **NOx** - Nitrogen oxides (µg/m³)
- **NO₂** - Nitrogen dioxide (µg/m³)
- **PM10** - Particulate matter <10µm (µg/m³)
- **PM2.5** - Fine particulate matter <2.5µm (µg/m³)
- Grid coordinates (British National Grid - will need conversion to WGS84)

### Using LAEI Data

1. Download the concentration CSV files
2. Each row is a 20m x 20m grid cell with Easting/Northing coordinates
3. For each school, find the nearest grid cell or the cell containing the school
4. Extract the modelled concentrations

**Note:** LAEI coordinates are in British National Grid (EPSG:27700). Your school data is in WGS84 (lon/lat). You'll need to convert.

```python
from pyproj import Transformer

# BNG to WGS84 conversion
transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)

# Convert Easting, Northing to Longitude, Latitude
lon, lat = transformer.transform(easting, northing)
```

---

## Your School Data Summary

Your `schools.geojson` contains **133 schools** in Lambeth and Southwark:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [longitude, latitude]  // Already WGS84
  },
  "properties": {
    "name": "School Name",
    "urn": 123456,
    "phase": "Primary" or "Nursery",
    "postcode": "SW2 1PL",
    "local_authority": "Lambeth" or "Southwark"
  }
}
```

---

## Recommended Implementation Steps

### Step 1: Fetch and Store Sensor Locations

```python
# 1. Fetch LAQN sites
laqn_url = "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json"
laqn_sites = requests.get(laqn_url).json()['Sites']['Site']

# Filter for Lambeth/Southwark
target_boroughs = ['Lambeth', 'Southwark']
local_laqn = [s for s in laqn_sites if s.get('@LocalAuthorityName') in target_boroughs]

# 2. Register for Breathe London API and fetch their sensor list

# 3. Store both in your database with lat/lon coordinates
```

### Step 2: Calculate Distances

Use the Haversine formula to calculate distance from each school to each sensor:

```python
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two points"""
    R = 6371000  # Earth's radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

# For each school, find sensors within 500m
THRESHOLD = 500  # meters

for school in schools:
    school_lat = school['geometry']['coordinates'][1]
    school_lon = school['geometry']['coordinates'][0]
    
    nearby_sensors = []
    for sensor in all_sensors:
        distance = haversine(school_lat, school_lon, sensor['lat'], sensor['lon'])
        if distance <= THRESHOLD:
            nearby_sensors.append({
                'sensor': sensor,
                'distance': distance
            })
```

### Step 3: Apply Your Hierarchical Logic

```python
def get_data_source_for_school(school, laqn_sensors, breathe_sensors, laei_grid):
    """
    Hierarchical decision:
    1. LAQN within 500m -> use LAQN
    2. Else Breathe London within 500m -> use Breathe London
    3. Else -> use LAEI modelled data
    """
    school_lat = school['geometry']['coordinates'][1]
    school_lon = school['geometry']['coordinates'][0]
    
    # Check LAQN first
    for sensor in laqn_sensors:
        dist = haversine(school_lat, school_lon, sensor['lat'], sensor['lon'])
        if dist <= 500:
            return {
                'source': 'LAQN',
                'sensor_code': sensor['code'],
                'distance_m': dist,
                'real_time': True
            }
    
    # Check Breathe London
    for sensor in breathe_sensors:
        dist = haversine(school_lat, school_lon, sensor['lat'], sensor['lon'])
        if dist <= 500:
            return {
                'source': 'Breathe London',
                'sensor_id': sensor['id'],
                'distance_m': dist,
                'real_time': True
            }
    
    # Fall back to LAEI
    laei_value = get_laei_for_location(school_lat, school_lon, laei_grid)
    return {
        'source': 'LAEI 2022',
        'modelled_no2': laei_value['no2'],
        'modelled_pm25': laei_value['pm25'],
        'real_time': False,
        'note': 'Annual mean from 2022 emissions inventory'
    }
```

### Step 4: Store in Django Models

```python
# models.py
class Sensor(models.Model):
    SENSOR_TYPES = [
        ('LAQN', 'London Air Quality Network'),
        ('BREATHE', 'Breathe London'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    sensor_type = models.CharField(max_length=20, choices=SENSOR_TYPES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    site_type = models.CharField(max_length=50)  # Roadside, Background, etc.
    borough = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

class SchoolDataSource(models.Model):
    school = models.OneToOneField('School', on_delete=models.CASCADE)
    
    # Primary data source decision
    source_type = models.CharField(max_length=20)  # LAQN, BREATHE, LAEI
    sensor = models.ForeignKey(Sensor, null=True, blank=True, on_delete=models.SET_NULL)
    distance_to_sensor = models.IntegerField(null=True)  # meters
    
    # LAEI baseline (always stored for comparison)
    laei_no2 = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    laei_pm25 = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    laei_pm10 = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    
    decision_notes = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
```

---

## Key API Reference Links

| Resource | URL |
|----------|-----|
| LAQN API Documentation | http://api.erg.ic.ac.uk/AirQuality/help |
| LAQN Terms & Conditions | http://api.erg.ic.ac.uk/AirQuality/Information/Terms/pdf |
| Breathe London API Registration | https://www.breathelondon.org/developers |
| Breathe London Pilot Data | https://breathelondonpilot.org/ |
| LAEI 2022 Download | https://data.london.gov.uk/dataset/london-atmospheric-emissions-inventory-laei-2022-2lg5g/ |
| London Datastore Air Quality | https://data.london.gov.uk/air-quality/ |

---

## Data Attribution Requirements

**LAQN:** Free under UK Open Government Licence. Attribute to "London Air Quality Network / Imperial College London".

**Breathe London:** Requires attribution: "Contains Breathe London data licensed under the Open Government License v3.0" with link to https://www.breathelondon.org/

**LAEI:** Published by Greater London Authority under Open Government Licence.

---

## Next Steps

1. **Register for Breathe London API** (takes a few days for approval)
2. **Download LAEI 2022 concentration CSV** from London Datastore
3. **Run a script** to fetch LAQN sensor locations and calculate distances to your 133 schools
4. **Categorize schools** into three groups:
   - Has LAQN sensor within 500m
   - Has Breathe London sensor within 500m
   - Will use LAEI modelled data
5. **Build your Django data pipeline** to fetch and store readings
