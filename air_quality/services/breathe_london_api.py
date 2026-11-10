"""
Breathe London API Service

Breathe London operates ~600+ low-cost sensors across London, calibrated against
reference-grade monitors.

API Documentation: https://www.breathelondon.org/developers
"""

import requests
import time
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)
# Species names in SensorData rows -> our field names.
# The index values (NO2Index, PM25Index) aren't in here, so they're ignored.
SPECIES_MAP = {
    'NO2': 'no2',
    'PM2.5': 'pm25',
    'PM25': 'pm25',
    'PM10': 'pm10',
}


class BreatheLondonApi:
    """
    Client for accessing Breathe London sensor data via their official API.
    """
    
    BASE_URL = "https://breathe-london-7x54d7qf.ew.gateway.dev"
    
    def __init__(self, api_key: str):
        """
        Initialize with Breathe London API key.
        
        Args:
            api_key: Your Breathe London API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make authenticated request to Breathe London API."""
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_sensors_by_borough(
        self,
        boroughs: list = None
    ) -> list:
        """
        Get sensors within specific boroughs.
        
        Args:
            boroughs: List of borough names (e.g., ["Lambeth", "Southwark"])
            
        Returns:
            List of sensor dictionaries
        """
        if boroughs is None:
            boroughs = ["Lambeth", "Southwark"]
        
        all_sensors = []
        for borough in boroughs:
            params = {"Borough": borough}
            data = self._make_request("ListSensors", params)
            return data if isinstance(data, list) else []
        

            
            # API returns list directly
            if isinstance(data, list):
                all_sensors.extend(data)
            else:
                logger.warning(f"Unexpected response format for borough {borough}")
        
        return all_sensors
    
    def get_sensors_in_radius(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0
    ) -> list:
        """
        Get sensors within a radius of a point.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Radius in kilometers
            
        Returns:
            List of sensor dictionaries
        """
        params = {
            "Latitude": latitude,
            "Longitude": longitude,
            "RadiusKM": radius_km
        }
        
        data = self._make_request("SensorData", params)
        return data if isinstance(data, list) else []
    
    def get_period_means(
        self,
        site_code: str,
        start: datetime,
        end: datetime,
        min_capture: float = 0.75,
    ) -> dict:
        """
        Average each pollutant over a period, from the hourly data.
        
        `end` is not included: 1 Nov 2025 to 1 Nov 2026 covers
        November 2025 to October 2026.
        
        Fetches one month per request. The API includes the end hour, so
        the first hour of each month comes back twice. Storing values by
        hour in a dictionary keeps only one copy.
        
        A pollutant is only included if at least `min_capture` of the
        period's hours have a value (75% is the usual rule).
        
        Returns e.g.
        {'no2': 24.3, 'pm25': 8.1, 'capture': {'no2': 0.98, 'pm25': 0.97}}
        """
        # One dictionary per pollutant: {hour: value}
        hourly = {col: {} for col in set(SPECIES_MAP.values())}
        
        month_start = start
        while month_start < end:
            # First day of the next month (December rolls over to January)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            month_end = min(month_end, end)
            
            # The API sometimes answers 500 (server error) after many requests
            # in a row. Wait and try again, up to 3 tries in all.
            for attempt in range(3):
                try:
                    rows = self.get_sensor_data(
                        site_code=site_code, start_time=month_start, end_time=month_end
                    )
                    break
                except requests.exceptions.HTTPError:
                    if attempt == 2:
                        raise
                    time.sleep(10 * (attempt + 1))
            time.sleep(1)  # be gentle: about one request a second
            
            for row in rows:
                col = SPECIES_MAP.get(row.get('Species'))
                value = row.get('ScaledValue')
                stamp = row.get('DateTime')
                if col is None or value is None or not stamp:
                    continue
                hour = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                hour = hour.replace(minute=0, second=0, microsecond=0)
                if start <= hour < end:
                    hourly[col][hour] = float(value)
            
            month_start = month_end
        
        hours_in_period = (end - start).total_seconds() / 3600
        means = {}
        capture = {}
        for col, values in hourly.items():
            if not values:
                continue
            capture[col] = round(len(values) / hours_in_period, 3)
            if capture[col] >= min_capture:
                means[col] = round(sum(values.values()) / len(values), 2)
            else:
                logger.info(
                    f"Breathe {site_code} {col}: capture {capture[col]:.0%} "
                    f"below {min_capture:.0%}, skipped"
                )
        
        means['capture'] = capture
        return means
    
    def get_sensor_data(
        self,
        site_code: str = None,
        borough: str = None,
        species: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> list:
        """
        Get sensor measurement data.
        
        Args:
            site_code: Specific site code (e.g., "BL0001")
            borough: Borough name
            species: Pollutant (NO2, PM25, NO2Index, PM25Index)
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            List of measurement dictionaries
        """
        params = {}
        
        if site_code:
            params["SiteCode"] = site_code
        if borough:
            params["Borough"] = borough
        if species:
            params["Species"] = species
        if start_time:
            # Convert to UTC and format without timezone suffix, then add Z
            params["startTime"] = start_time.astimezone(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        if end_time:
            params["endTime"] = end_time.astimezone(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        
        data = self._make_request("SensorData", params)
        return data if isinstance(data, list) else []


def test_connection(api_key: str) -> bool:
    """
    Test API connection and key validity.
    
    Args:
        api_key: Breathe London API key
        
    Returns:
        True if connection successful
    """
    try:
        api = BreatheLondonApi(api_key)
        # Try to fetch sensors for Lambeth
        sensors = api.get_sensors_by_borough(["Lambeth"])
        print(f"✓ Connection successful. Found {len(sensors)} sensors in Lambeth.")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


# Parameter mapping for our database
PARAMETER_MAP = {
    "NO2": "no2",
    "PM25": "pm25",
    "PM10": "pm10",
}
