"""
London Air Quality Network (LAQN) API Service

LAQN provides reference-grade monitoring data across London.
No API key required - data is available under UK Open Government Licence.

API Documentation: https://www.londonair.org.uk/LondonAir/API/
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class LAQNApi:
    """
    Client for accessing LAQN monitoring data.
    
    LAQN sensors are reference-grade instruments maintained by London
    boroughs and provide the most accurate readings available.
    """
    
    BASE_URL = "https://api.erg.ic.ac.uk/AirQuality"
    
    def __init__(self):
        """Initialize LAQN client. No API key required."""
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make request to LAQN API."""
        url = f"{self.BASE_URL}/{endpoint}/Json"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"LAQN API request failed: {e}")
            raise
    
    def get_monitoring_sites(
        self,
        borough: str = None,
        site_type: str = None
    ) -> List[dict]:
        """
        Get list of monitoring sites.
        
        Args:
            borough: Filter by borough name (e.g., "Lambeth")
            site_type: Filter by type (e.g., "Roadside", "Background")
            
        Returns:
            List of site dictionaries
        """
        # LAQN API requires fetching all London sites, then filtering
        data = self._make_request("Information/MonitoringSiteSpecies/GroupName=London")
        
        # Handle LAQN's quirky response format
        sites = data.get("Sites", {}).get("Site", [])
        
        # Ensure it's always a list (single item comes as dict)
        if isinstance(sites, dict):
            sites = [sites]
        
        # Filter by borough if specified
        if borough:
            sites = [s for s in sites if s.get("@LocalAuthorityName", "").lower() == borough.lower()]
        
        # Filter by site type if specified
        if site_type:
            sites = [s for s in sites if site_type.lower() in s.get("@SiteType", "").lower()]
        
        return sites
    
    def get_site_data(self, site_code: str) -> dict:
        """
        Get detailed information about a specific site.
        
        Args:
            site_code: Site code (e.g., "LB4")
            
        Returns:
            Site details dictionary
        """
        data = self._make_request(f"Information/MonitoringSite/SiteCode={site_code}")
        return data.get("SiteInfo", {})
    
    def get_hourly_readings(
        self,
        site_code: str,
        start_date: datetime = None,
        end_date: datetime = None,
        species: str = None
    ) -> List[dict]:
        """
        Get hourly readings for a site.
        
        Args:
            site_code: Site code
            start_date: Start of date range (default: yesterday)
            end_date: End of date range (default: today)
            species: Specific pollutant (NO2, PM25, PM10, O3) or all
            
        Returns:
            List of reading dictionaries
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=1)
        if end_date is None:
            end_date = datetime.now()
        
        start_str = start_date.strftime("%d%b%Y")
        end_str = end_date.strftime("%d%b%Y")
        
        endpoint = f"Data/SiteSpecies/SiteCode={site_code}/StartDate={start_str}/EndDate={end_str}"
        
        if species:
            endpoint += f"/SpeciesCode={species}"
        
        data = self._make_request(endpoint)
        
        # Parse the nested response
        readings = []
        site_data = data.get("RawAQData", {}).get("Data", [])
        
        if isinstance(site_data, dict):
            site_data = [site_data]
        
        for species_data in site_data:
            species_code = species_data.get("@SpeciesCode")
            values = species_data.get("Data", [])
            
            if isinstance(values, dict):
                values = [values]
            
            for v in values:
                readings.append({
                    'species': species_code,
                    'timestamp': v.get("@MeasurementDateGMT"),
                    'value': v.get("@Value"),
                })
        
        return readings
    
    def get_latest_readings(
        self,
        borough: str = None,
        site_code: str = None
    ) -> List[dict]:
        """
        Get latest readings from sites.
        
        Args:
            borough: Filter by borough
            site_code: Specific site code
            
        Returns:
            List of latest readings
        """
        if site_code:
            endpoint = f"Hourly/MonitoringIndex/SiteCode={site_code}/GroupName=London"
        elif borough:
            endpoint = f"Hourly/MonitoringIndex/Authority={borough}/GroupName=London"
        else:
            endpoint = "Hourly/MonitoringIndex/GroupName=London"
        
        data = self._make_request(endpoint)
        
        sites = data.get("HourlyAirQualityIndex", {}).get("LocalAuthority", [])
        if isinstance(sites, dict):
            sites = [sites]
        
        readings = []
        for authority in sites:
            site_list = authority.get("Site", [])
            if isinstance(site_list, dict):
                site_list = [site_list]
            
            for site in site_list:
                species = site.get("Species", [])
                if isinstance(species, dict):
                    species = [species]
                
                for s in species:
                    readings.append({
                        'site_code': site.get("@SiteCode"),
                        'site_name': site.get("@SiteName"),
                        'species': s.get("@SpeciesCode"),
                        'value': s.get("@AirQualityIndex"),
                        'band': s.get("@AirQualityBand"),
                    })
        
        return readings
    
    def get_annual_mean(
        self,
        site_code: str,
        year: int,
        species: str = "NO2"
    ) -> Optional[float]:
        """
        Get annual mean concentration for a site.
        
        Args:
            site_code: Site code
            year: Year to retrieve
            species: Pollutant code
            
        Returns:
            Annual mean in µg/m³ or None
        """
        endpoint = f"Annual/MonitoringObjective/SiteCode={site_code}/Year={year}"
        
        try:
            data = self._make_request(endpoint)
            objectives = data.get("SiteObjectives", {}).get("Objective", [])
            
            if isinstance(objectives, dict):
                objectives = [objectives]
            
            for obj in objectives:
                if obj.get("@SpeciesCode") == species:
                    value = obj.get("@Value")
                    if value:
                        return float(value)
        except Exception as e:
            logger.warning(f"Could not get annual mean for {site_code}: {e}")
        
        return None


def test_connection() -> bool:
    """Test LAQN API connection."""
    try:
        api = LAQNApi()
        sites = api.get_monitoring_sites(borough="Lambeth")
        print(f"✓ LAQN connection successful. Found {len(sites)} sites in Lambeth.")
        return True
    except Exception as e:
        print(f"✗ LAQN connection failed: {e}")
        return False
