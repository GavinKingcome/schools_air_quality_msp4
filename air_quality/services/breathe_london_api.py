"""
Breathe London API Service

Breathe London operates ~600+ low-cost sensors across London, calibrated against
reference-grade monitors.

API Documentation: https://www.breathelondon.org/developers
"""

import requests
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


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
        
        data = self._make_request("ListSensors", params)
        return data if isinstance(data, list) else []
    
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
