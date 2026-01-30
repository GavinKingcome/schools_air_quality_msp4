#!/usr/bin/env python3
"""
LAEI ASCII Raster Extraction for Schools
=========================================

Run this script LOCALLY on your machine where the LAEI .asc files are stored.

It reads the ESRI ASCII Grid format (.asc) files and extracts concentration
values for each school location.

Usage:
    1. Update the paths below to point to your files
    2. Run: python extract_laei_local.py
    3. Output: schools_with_laei.json and schools_with_laei.csv

Requirements:
    - Python 3.7+
    - No external packages required (uses only standard library)
    - Optional: pip install pyproj (for precise coordinate conversion)
"""

import json
import csv
import math
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION - UPDATED FOR YOUR SYSTEM
# ============================================================================

# Folder containing the extracted LAEI ASCII files
LAEI_FOLDER = "/Users/GK/Documents/vscode-projects/schools_air_quality_msp4/LAEI/ASCII"

# Map of pollutants to their .asc filenames
ASC_FILES = {
    'NO2': 'LAEI2022_V1_NO2.asc',
    'NOx': 'LAEI2022_V1_NOx.asc',
    'PM25': 'LAEI2022_V1_PM25.asc',
    'PM10_mean': 'LAEI2022_V1_PM10m.asc',   # Annual mean
    'PM10_days': 'LAEI2022_V1_PM10d.asc',   # Days exceeding limit
}

# Your schools GeoJSON file
SCHOOLS_GEOJSON = "/Users/GK/Documents/vscode-projects/schools_air_quality_msp4/schools.geojson"

# Output files
OUTPUT_JSON = "/Users/GK/Documents/vscode-projects/schools_air_quality_msp4/schools_with_laei.json"
OUTPUT_CSV = "/Users/GK/Documents/vscode-projects/schools_air_quality_msp4/schools_with_laei.csv"
OUTPUT_SUMMARY = "/Users/GK/Documents/vscode-projects/schools_air_quality_msp4/laei_summary.json"

# ============================================================================
# COORDINATE CONVERSION
# ============================================================================

def wgs84_to_bng(latitude, longitude):
    """
    Convert WGS84 (lat/lon) to British National Grid (easting/northing).
    
    Uses pyproj if available, otherwise falls back to approximation.
    """
    try:
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
        easting, northing = transformer.transform(longitude, latitude)
        return easting, northing
    except ImportError:
        # Fallback approximation for London (accurate to ~10-15m)
        # Good enough for 20m grid cells
        lon0, lat0 = -0.1, 51.5
        e0, n0 = 530000, 180000
        m_per_deg_lon = 111320 * math.cos(math.radians(lat0))
        m_per_deg_lat = 110540
        easting = e0 + (longitude - lon0) * m_per_deg_lon
        northing = n0 + (latitude - lat0) * m_per_deg_lat
        return easting, northing


# ============================================================================
# ESRI ASCII GRID READER
# ============================================================================

class ASCIIGrid:
    """
    Reader for ESRI ASCII Grid format (.asc files).
    
    Format:
        ncols         2900
        nrows         2400
        xllcorner     503000
        yllcorner     155000
        cellsize      20
        NODATA_value  -9999
        12.4 13.1 14.2 ...
        ...
    """
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.ncols = 0
        self.nrows = 0
        self.xllcorner = 0  # X (easting) of lower-left corner
        self.yllcorner = 0  # Y (northing) of lower-left corner
        self.cellsize = 20
        self.nodata = -9999
        self.data = []
        
        self._load()
    
    def _load(self):
        """Load the ASCII grid file."""
        print(f"   Loading: {os.path.basename(self.filepath)}...")
        
        with open(self.filepath, 'r') as f:
            # Read header (6 lines)
            for _ in range(6):
                line = f.readline().strip()
                key, value = line.split()
                key = key.lower()
                
                if key == 'ncols':
                    self.ncols = int(value)
                elif key == 'nrows':
                    self.nrows = int(value)
                elif key == 'xllcorner':
                    self.xllcorner = float(value)
                elif key == 'yllcorner':
                    self.yllcorner = float(value)
                elif key == 'cellsize':
                    self.cellsize = float(value)
                elif key in ['nodata_value', 'nodata']:
                    self.nodata = float(value)
            
            print(f"      Grid: {self.ncols} x {self.nrows} cells")
            print(f"      Origin: ({self.xllcorner}, {self.yllcorner})")
            print(f"      Cell size: {self.cellsize}m")
            
            # Read data rows
            # Note: Row 0 in file = top (north), so we read top-to-bottom
            row_count = 0
            for line in f:
                values = line.strip().split()
                row = [float(v) for v in values]
                self.data.append(row)
                row_count += 1
                
                if row_count % 500 == 0:
                    print(f"      Read {row_count}/{self.nrows} rows...")
            
            print(f"      Complete: {len(self.data)} rows loaded")
    
    def get_value(self, easting, northing):
        """
        Get the grid value at a specific BNG coordinate.
        
        Returns: concentration value, or None if outside grid or NODATA
        """
        # Calculate column (x) and row (y) indices
        col = int((easting - self.xllcorner) / self.cellsize)
        
        # Rows are stored top-to-bottom, but coordinates are bottom-to-top
        # So row 0 in data = northernmost row
        row_from_bottom = int((northing - self.yllcorner) / self.cellsize)
        row = self.nrows - 1 - row_from_bottom
        
        # Check bounds
        if col < 0 or col >= self.ncols or row < 0 or row >= self.nrows:
            return None
        
        value = self.data[row][col]
        
        # Check for NODATA
        if value == self.nodata or value < 0:
            return None
        
        return value


# ============================================================================
# MAIN EXTRACTION
# ============================================================================

def load_schools(geojson_path):
    """Load schools from GeoJSON file."""
    print(f"\n📚 Loading schools from: {os.path.basename(geojson_path)}")
    
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    schools = []
    for feature in data['features']:
        coords = feature['geometry']['coordinates']
        props = feature['properties']
        
        schools.append({
            'name': props.get('name', 'Unknown'),
            'urn': props.get('urn'),
            'phase': props.get('phase', ''),
            'postcode': props.get('postcode', ''),
            'borough': props.get('local_authority', ''),
            'longitude': coords[0],
            'latitude': coords[1]
        })
    
    print(f"   Loaded {len(schools)} schools")
    return schools


def extract_values(schools, grids):
    """
    Extract concentration values for each school from all grids.
    
    Args:
        schools: List of school dictionaries
        grids: Dict of pollutant_name -> ASCIIGrid
    
    Returns:
        List of enriched school dictionaries
    """
    print(f"\n🔗 Extracting values for {len(schools)} schools...")
    
    enriched = []
    found_count = 0
    
    for i, school in enumerate(schools):
        # Convert coordinates
        easting, northing = wgs84_to_bng(school['latitude'], school['longitude'])
        
        # Extract values from each grid
        concentrations = {}
        has_data = False
        
        for pollutant, grid in grids.items():
            value = grid.get_value(easting, northing)
            if value is not None:
                concentrations[f'{pollutant}_2022'] = round(value, 2)
                has_data = True
            else:
                concentrations[f'{pollutant}_2022'] = None
        
        if has_data:
            found_count += 1
        
        enriched_school = school.copy()
        enriched_school['bng_easting'] = round(easting, 1)
        enriched_school['bng_northing'] = round(northing, 1)
        enriched_school['laei_found'] = has_data
        enriched_school['concentrations'] = concentrations
        
        enriched.append(enriched_school)
        
        # Progress indicator
        if (i + 1) % 25 == 0:
            print(f"   Processed {i + 1}/{len(schools)} schools...")
    
    print(f"\n   ✅ Values found for {found_count}/{len(schools)} schools")
    
    return enriched


def save_outputs(schools, output_json, output_csv):
    """Save results to JSON and CSV files."""
    
    print(f"\n💾 Saving outputs...")
    
    # JSON output
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(schools, f, indent=2, ensure_ascii=False)
    print(f"   ✓ {os.path.basename(output_json)}")
    
    # CSV output
    if schools:
        # Get all concentration columns
        conc_cols = sorted(schools[0].get('concentrations', {}).keys())
        
        fieldnames = [
            'name', 'urn', 'phase', 'borough', 'postcode',
            'latitude', 'longitude', 'bng_easting', 'bng_northing',
            'laei_found'
        ] + conc_cols
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for school in schools:
                row = {
                    'name': school['name'],
                    'urn': school['urn'],
                    'phase': school['phase'],
                    'borough': school['borough'],
                    'postcode': school['postcode'],
                    'latitude': school['latitude'],
                    'longitude': school['longitude'],
                    'bng_easting': school.get('bng_easting'),
                    'bng_northing': school.get('bng_northing'),
                    'laei_found': school.get('laei_found', False)
                }
                
                for col in conc_cols:
                    row[col] = school.get('concentrations', {}).get(col, '')
                
                writer.writerow(row)
        
        print(f"   ✓ {os.path.basename(output_csv)}")


def print_summary(schools):
    """Print a summary of the extracted data and return summary dict."""
    
    found = [s for s in schools if s.get('laei_found')]
    
    print("\n" + "="*70)
    print("                         SUMMARY")
    print("="*70)
    
    print(f"\n📊 Coverage: {len(found)}/{len(schools)} schools with LAEI data")
    
    # Initialize summary dictionary
    summary = {
        'total_schools': len(schools),
        'schools_with_data': len(found),
        'coverage_percent': round(len(found) / len(schools) * 100, 1) if schools else 0,
        'pollutants': {},
        'no2_guidelines': {},
        'top_5_by_pollutant': {}
    }
    
    if not found:
        print("\n   ⚠️  No data found - check file paths and coordinate conversion")
        return summary
    
    # Get concentration columns
    conc_keys = list(found[0].get('concentrations', {}).keys())
    
    print(f"\n📈 Pollutant Values (µg/m³):")
    
    for key in sorted(conc_keys):
        values = [s['concentrations'].get(key) 
                  for s in found 
                  if s['concentrations'].get(key) is not None]
        
        if values:
            min_val = min(values)
            max_val = max(values)
            mean_val = sum(values) / len(values)
            
            print(f"\n   {key}:")
            print(f"      Min:  {min_val:.1f}")
            print(f"      Max:  {max_val:.1f}")
            print(f"      Mean: {mean_val:.1f}")
            
            summary['pollutants'][key] = {
                'min': round(min_val, 2),
                'max': round(max_val, 2),
                'mean': round(mean_val, 2),
                'count': len(values)
            }
    
    # Health guideline comparison (for NO2)
    no2_key = next((k for k in conc_keys if 'NO2' in k.upper()), None)
    if no2_key:
        values = [s['concentrations'].get(no2_key) 
                  for s in found 
                  if s['concentrations'].get(no2_key) is not None]
        
        above_40 = sum(1 for v in values if v > 40)
        above_20 = sum(1 for v in values if v > 20)
        above_10 = sum(1 for v in values if v > 10)
        
        print(f"\n📋 NO₂ vs Regulatory Standards ({len(values)} schools):")
        print(f"   Above UK limit (40 µg/m³):           {above_40} ({above_40/len(values)*100:.1f}%)")
        print(f"   Above EU 2024 target (20 µg/m³):     {above_20} ({above_20/len(values)*100:.1f}%)")
        print(f"   Above WHO 2021 guideline (10 µg/m³): {above_10} ({above_10/len(values)*100:.1f}%)")
        
        summary['no2_guidelines'] = {
            'total_schools': len(values),
            'above_uk_limit_40': above_40,
            'above_eu_2024_target_20': above_20,
            'above_who_2021_guideline_10': above_10,
            'percent_above_uk_limit': round(above_40 / len(values) * 100, 1) if values else 0,
            'percent_above_eu_2024_target': round(above_20 / len(values) * 100, 1) if values else 0,
            'percent_above_who_2021_guideline': round(above_10 / len(values) * 100, 1) if values else 0,
            'note': 'UK continues with 40 µg/m³ limit while EU adopted stricter 20 µg/m³ target for 2030'
        }
    
    # Borough comparison (for NO2)
    if no2_key:
        print(f"\n🏛️  Borough Comparison (NO₂):")
        
        summary['borough_comparison'] = {}
        
        # Group schools by borough
        boroughs = {}
        for school in found:
            no2_val = school['concentrations'].get(no2_key)
            if no2_val is not None:
                borough = school.get('borough', 'Unknown')
                if borough not in boroughs:
                    boroughs[borough] = []
                boroughs[borough].append(no2_val)
        
        for borough in sorted(boroughs.keys()):
            values = boroughs[borough]
            above_40 = sum(1 for v in values if v > 40)
            above_20 = sum(1 for v in values if v > 20)
            above_10 = sum(1 for v in values if v > 10)
            mean_val = sum(values) / len(values)
            
            print(f"\n   {borough} ({len(values)} schools):")
            print(f"      Mean NO₂: {mean_val:.1f} µg/m³")
            print(f"      Above UK limit (40):             {above_40} ({above_40/len(values)*100:.1f}%)")
            print(f"      Above EU 2024 target (20):       {above_20} ({above_20/len(values)*100:.1f}%)")
            print(f"      Above WHO 2021 guideline (10):   {above_10} ({above_10/len(values)*100:.1f}%)")
            
            summary['borough_comparison'][borough] = {
                'total_schools': len(values),
                'mean_no2': round(mean_val, 2),
                'min_no2': round(min(values), 2),
                'max_no2': round(max(values), 2),
                'above_uk_limit_40': above_40,
                'above_eu_2024_target_20': above_20,
                'above_who_2021_guideline_10': above_10,
                'percent_above_uk_limit': round(above_40 / len(values) * 100, 1),
                'percent_above_eu_2024_target': round(above_20 / len(values) * 100, 1),
                'percent_above_who_2021_guideline': round(above_10 / len(values) * 100, 1)
            }
    
    # Top 5 most polluted for each pollutant
    print(f"\n🏫 Top 5 Schools by Pollutant:")
    
    for key in sorted(conc_keys):
        schools_with_value = [s for s in found if s['concentrations'].get(key) is not None]
        
        if schools_with_value:
            sorted_schools = sorted(
                schools_with_value,
                key=lambda x: x['concentrations'][key],
                reverse=True
            )
            
            pollutant_name = key.replace('_2022', '').replace('_', ' ').upper()
            print(f"\n   {pollutant_name}:")
            
            top_5 = []
            for i, school in enumerate(sorted_schools[:5], 1):
                val = school['concentrations'][key]
                print(f"      {i}. {school['name'][:42]}: {val:.1f} µg/m³")
                
                top_5.append({
                    'rank': i,
                    'name': school['name'],
                    'value': round(val, 2),
                    'postcode': school.get('postcode', ''),
                    'borough': school.get('borough', '')
                })
            
            summary['top_5_by_pollutant'][key] = top_5
    
    print("\n" + "="*70)
    
    return summary


def main():
    print("\n" + "="*70)
    print("   LAEI ASCII GRID EXTRACTION FOR LAMBETH & SOUTHWARK SCHOOLS")
    print("="*70)
    
    # Check LAEI folder exists
    if not os.path.isdir(LAEI_FOLDER):
        print(f"\n❌ LAEI folder not found: {LAEI_FOLDER}")
        print("   Please update LAEI_FOLDER path at the top of this script")
        return
    
    # Load schools
    if os.path.exists(SCHOOLS_GEOJSON):
        schools = load_schools(SCHOOLS_GEOJSON)
    else:
        print(f"\n❌ Schools file not found: {SCHOOLS_GEOJSON}")
        print("   Please update SCHOOLS_GEOJSON path at the top of this script")
        return
    
    # Load each ASCII grid
    print(f"\n🗺️  Loading LAEI ASCII grids from: {os.path.basename(LAEI_FOLDER)}")
    
    grids = {}
    for pollutant, filename in ASC_FILES.items():
        filepath = os.path.join(LAEI_FOLDER, filename)
        
        if os.path.exists(filepath):
            grids[pollutant] = ASCIIGrid(filepath)
        else:
            print(f"   ⚠️  File not found: {filename}")
    
    if not grids:
        print("\n❌ No LAEI grid files found. Check the filenames in ASC_FILES.")
        return
    
    print(f"\n   Loaded {len(grids)} pollutant grids: {', '.join(grids.keys())}")
    
    # Extract values for each school
    enriched_schools = extract_values(schools, grids)
    
    # Print summary and get summary data
    summary = print_summary(enriched_schools)
    
    # Save outputs
    save_outputs(enriched_schools, OUTPUT_JSON, OUTPUT_CSV)
    
    # Save summary statistics
    print(f"\n💾 Saving summary statistics...")
    with open(OUTPUT_SUMMARY, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"   ✓ {os.path.basename(OUTPUT_SUMMARY)}")
    
    print(f"\n✅ Complete!")
    print(f"\n   Next steps:")
    print(f"   1. Open {os.path.basename(OUTPUT_CSV)} in Excel to review")
    print(f"   2. Review {os.path.basename(OUTPUT_SUMMARY)} for statistics")
    print(f"   3. Import {os.path.basename(OUTPUT_JSON)} into your Django app")
    print(f"   4. Use: python manage.py import_laei {os.path.basename(OUTPUT_JSON)}")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
