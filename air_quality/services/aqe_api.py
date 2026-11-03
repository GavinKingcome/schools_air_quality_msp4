"""
Air Quality England (AQE) data service.

Air Quality England is run by Ricardo Energy & Environment. It hosts the
reference-grade stations that some boroughs choose not to run through the
London Air Quality Network (LAQN). Southwark moved four of its five stations
here in March 2025.

There is no JSON API. Ricardo publishes one .RData file per site per year,
updated daily, on a public server. This is the same feed the openair R
package uses. We read the files with pyreadr, so no R install is needed.

Things to know:
- Times in these files are hour BEGINNING. LAQN times are hour ENDING.
  get_hourly() shifts AQE times forward by one hour so the two line up.
- Files update once a day. This is not a live feed. For the Tier 2
  adjustment factor that is fine.
- Site codes are upper case, e.g. SWK12.
- The file name pattern and column names below are taken from the openair
  source. They have not been checked against a live download from inside
  this project, so run `sync_aqe_sensors --show-columns` first.

Requires: pip install pyreadr pandas
"""

import calendar
import logging
import tempfile
from datetime import timedelta
from typing import Optional

import pandas as pd
import pyreadr
import requests

logger = logging.getLogger(__name__)


# Column names in the Ricardo files -> field names on our Reading model
POLLUTANT_MAP = {
    'no2': 'no2',
    'pm2.5': 'pm25',
    'pm10': 'pm10',
    'o3': 'o3',
    'nox': 'nox',
}


class AQEApi:
    """
    Client for the Air Quality England openair file server.
    No API key is needed.
    """

    BASE_URL = "https://airqualityengland.co.uk/assets/openair/R_data/"
    META_FILE = "AQE_metadata.RData"

    def __init__(self):
        self.session = requests.Session()
        self._meta = None  # cached metadata table

    # ------------------------------------------------------------------
    # Low level
    # ------------------------------------------------------------------

    def _fetch_rdata(self, filename: str) -> Optional[pd.DataFrame]:
        """
        Download one .RData file and return it as a DataFrame.
        Returns None if the file does not exist (404).
        """
        url = f"{self.BASE_URL}{filename}"
        response = self.session.get(url, timeout=60)

        if response.status_code == 404:
            logger.info(f"AQE: no file at {url}")
            return None
        response.raise_for_status()
        
        # A web page instead of a data file usually means the site is down
        # for maintenance. Say so plainly instead of letting pyreadr fail.
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type or response.content[:1] == b"<":
            raise RuntimeError(
                f"AQE server returned a web page, not a data file, for {url}. "
                f"The site may be down for maintenance."
            )

        # pyreadr needs a real file on disk, not a bytes object
        with tempfile.NamedTemporaryFile(suffix=".RData") as tmp:
            tmp.write(response.content)
            tmp.flush()
            result = pyreadr.read_r(tmp.name)

        # Each file holds one R object. Take the first (and only) one.
        return next(iter(result.values()))

    # ------------------------------------------------------------------
    # Site metadata
    # ------------------------------------------------------------------

    def get_metadata(self) -> Optional[pd.DataFrame]:
        """Return the full metadata table, cached for this client."""
        if self._meta is None:
            self._meta = self._fetch_rdata(self.META_FILE)
        return self._meta

    def get_sites(self, local_authorities: list = None) -> list:
        """
        Get a list of sites, one dict per site.

        The metadata table has one row per site AND pollutant, so a site
        with four pollutants appears four times. We keep one row per site.

        Expected columns (check with --show-columns on first run):
            code, site, site_type, latitude, longitude,
            start_date, end_date, local_authority
        """
        meta = self.get_metadata()
        if meta is None or meta.empty:
            return []

        sites = meta.drop_duplicates(subset='code')

        if local_authorities:
            wanted = {la.lower() for la in local_authorities}
            sites = sites[sites['local_authority'].str.lower().isin(wanted)]

        return sites.to_dict('records')

    # ------------------------------------------------------------------
    # Readings
    # ------------------------------------------------------------------

    def get_hourly(
        self,
        site_code: str,
        year: int,
        hour_ending: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Get all hourly readings for one site in one year.

        Returns a DataFrame with a 'date' column (UTC, timezone-aware)
        plus whichever of no2, pm25, pm10, o3, nox the site measures.
        Returns None if there is no file for that site/year.
        """
        df = self._fetch_rdata(f"{site_code.upper()}_{year}.RData")
        if df is None or df.empty:
            return None

        df = df.rename(columns=POLLUTANT_MAP)
        keep = ['date'] + [c for c in POLLUTANT_MAP.values() if c in df.columns]
        df = df[keep].copy()

        df['date'] = pd.to_datetime(df['date'], utc=True)
        if hour_ending:
            # Ricardo files are hour beginning; LAQN is hour ending.
            df['date'] = df['date'] + timedelta(hours=1)

        return df

    def get_annual_means(
        self,
        site_code: str,
        year: int,
        min_capture: float = 0.75,
    ) -> dict:
        """
        Calculate annual mean per pollutant from the hourly file.

        A pollutant is only included if at least `min_capture` of the
        year's hours have a value. 75% is the usual Local Air Quality
        Management threshold.

        Returns e.g. {'no2': 31.4, 'pm25': 9.8, 'pm10': 17.2}
        """
        df = self.get_hourly(site_code, year, hour_ending=False)
        if df is None:
            return {}

        hours_in_year = 8784 if calendar.isleap(year) else 8760
        means = {}

        for col in POLLUTANT_MAP.values():
            if col not in df.columns:
                continue
            capture = df[col].notna().sum() / hours_in_year
            if capture >= min_capture:
                means[col] = round(float(df[col].mean()), 2)
            else:
                logger.info(
                    f"AQE {site_code} {year} {col}: capture {capture:.0%} "
                    f"below {min_capture:.0%}, skipped"
                )

        return means


def test_connection() -> bool:
    """Quick check that the metadata file can be reached and read."""
    try:
        api = AQEApi()
        sites = api.get_sites(['Southwark'])
        print(f"✓ AQE connection successful. Found {len(sites)} sites in Southwark.")
        for s in sites:
            print(f"   {s.get('code')}  {s.get('site')}  ({s.get('site_type')})")
        return True
    except Exception as e:
        print(f"✗ AQE connection failed: {e}")
        return False
