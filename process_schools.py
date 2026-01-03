#!/usr/bin/env python3
"""
process_schools.py

Process GIAS (Get Information About Schools) data to extract nurseries 
and primary schools in Southwark and Lambeth for air quality monitoring.

Usage:
    1. Download GIAS data from: https://get-information-schools.service.gov.uk/
       - Search by Local Authority for Southwark, then Lambeth
       - Download CSV for each
    
    OR download the full dataset from the API:
       http://ea-edubase-api-prod.azurewebsites.net/edubase/edubasealldata{YYYYMMDD}.csv
    
    2. Run this script:
       python process_schools.py --input gias_data.csv --output schools_filtered.csv

Requirements:
    pip install pandas pyproj
"""

import pandas as pd
import argparse
import json
from pathlib import Path

# Optional: for coordinate conversion from British National Grid to WGS84
try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False
    print("Note: Install pyproj for coordinate conversion: pip install pyproj")


def convert_bng_to_wgs84(easting, northing):
    """Convert British National Grid to WGS84 lat/lon."""
    if not HAS_PYPROJ:
        return None, None
    
    transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return lat, lon


def load_gias_data(filepath):
    """Load GIAS CSV data with proper encoding."""
    # GIAS files often have Windows-1252 or Latin-1 encoding
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding, low_memory=False)
            print(f"Loaded {len(df)} records using {encoding} encoding")
            return df
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Could not read file with any of these encodings: {encodings}")


def filter_schools(df, boroughs=None, phases=None, status='Open'):
    """Filter GIAS data for specific boroughs and school phases."""
    
    if boroughs is None:
        boroughs = ['Southwark', 'Lambeth']
    
    if phases is None:
        phases = ['Nursery', 'Primary', 'All-through']
    
    # Column names may vary slightly in GIAS exports
    la_column = None
    for col in ['LA (name)', 'LA Name', 'LocalAuthority']:
        if col in df.columns:
            la_column = col
            break
    
    if la_column is None:
        print("Available columns:", df.columns.tolist())
        raise ValueError("Could not find Local Authority column")
    
    phase_column = None
    for col in ['PhaseOfEducation (name)', 'Phase', 'PhaseOfEducation']:
        if col in df.columns:
            phase_column = col
            break
    
    status_column = None
    for col in ['EstablishmentStatus (name)', 'Status', 'EstablishmentStatus']:
        if col in df.columns:
            status_column = col
            break
    
    # Apply filters
    df_filtered = df.copy()
    
    # Filter by Local Authority
    df_filtered = df_filtered[df_filtered[la_column].isin(boroughs)]
    print(f"After LA filter: {len(df_filtered)} records")
    
    # Filter by phase
    if phase_column:
        df_filtered = df_filtered[df_filtered[phase_column].isin(phases)]
        print(f"After phase filter: {len(df_filtered)} records")
    
    # Filter by status
    if status_column and status:
        df_filtered = df_filtered[df_filtered[status_column] == status]
        print(f"After status filter: {len(df_filtered)} records")
    
    return df_filtered


def process_for_output(df):
    """Process dataframe and add lat/lon coordinates."""
    
    # Map column names (handle variations in GIAS exports)
    column_mapping = {
        'URN': 'urn',
        'EstablishmentName': 'name',
        'Establishment Name': 'name',
        'EstablishmentTypeGroup (name)': 'type',
        'TypeOfEstablishment (name)': 'type',
        'PhaseOfEducation (name)': 'phase',
        'Phase': 'phase',
        'Street': 'street',
        'Locality': 'locality',
        'Town': 'town',
        'Postcode': 'postcode',
        'Easting': 'easting',
        'Northing': 'northing',
        'LA (name)': 'local_authority',
        'LA Name': 'local_authority',
    }
    
    # Find which columns exist and rename
    rename_map = {}
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            rename_map[old_name] = new_name
    
    df_processed = df.rename(columns=rename_map)
    
    # Select only needed columns that exist
    desired_columns = ['urn', 'name', 'type', 'phase', 'street', 'locality', 
                       'town', 'postcode', 'easting', 'northing', 'local_authority']
    
    available_columns = [col for col in desired_columns if col in df_processed.columns]
    df_processed = df_processed[available_columns].copy()
    
    # Convert coordinates if easting/northing are present
    if 'easting' in df_processed.columns and 'northing' in df_processed.columns:
        if HAS_PYPROJ:
            print("Converting coordinates from British National Grid to WGS84...")
            lats = []
            lons = []
            for _, row in df_processed.iterrows():
                try:
                    e = float(row['easting']) if pd.notna(row['easting']) else None
                    n = float(row['northing']) if pd.notna(row['northing']) else None
                    if e and n:
                        lat, lon = convert_bng_to_wgs84(e, n)
                        lats.append(round(lat, 6))
                        lons.append(round(lon, 6))
                    else:
                        lats.append(None)
                        lons.append(None)
                except:
                    lats.append(None)
                    lons.append(None)
            
            df_processed['latitude'] = lats
            df_processed['longitude'] = lons
    
    return df_processed


def export_to_geojson(df, output_path):
    """Export schools to GeoJSON format for Leaflet mapping."""
    features = []
    
    lat_col = 'latitude' if 'latitude' in df.columns else None
    lon_col = 'longitude' if 'longitude' in df.columns else None
    
    for _, row in df.iterrows():
        if lat_col and lon_col and pd.notna(row[lat_col]) and pd.notna(row[lon_col]):
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row[lon_col]), float(row[lat_col])]
                
                },
                 "properties": {
                    "name": str(row.get('name', '')),
                    "urn": int(row['urn']) if pd.notna(row.get('urn')) else None,
                    "type": str(row.get('type', '')),
                    "phase": str(row.get('phase', '')),
                    "postcode": str(row.get('postcode', '')),
                    "local_authority": str(row.get('local_authority', ''))
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_path, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    print(f"Exported {len(features)} schools to GeoJSON: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Process GIAS schools data')
    parser.add_argument('--input', '-i', required=True, help='Input GIAS CSV file')
    parser.add_argument('--output', '-o', default='schools_processed.csv', help='Output CSV file')
    parser.add_argument('--geojson', '-g', help='Output GeoJSON file (optional)')
    parser.add_argument('--boroughs', nargs='+', default=['Southwark', 'Lambeth'],
                        help='Borough names to filter')
    parser.add_argument('--phases', nargs='+', default=['Nursery', 'Primary', 'All-through'],
                        help='School phases to include')
    
    args = parser.parse_args()
    
    # Load data
    print(f"\nLoading data from {args.input}...")
    df = load_gias_data(args.input)
    
    # Filter
    print(f"\nFiltering for boroughs: {args.boroughs}")
    print(f"Filtering for phases: {args.phases}")
    df_filtered = filter_schools(df, boroughs=args.boroughs, phases=args.phases)
    
    # Process
    print("\nProcessing data...")
    df_processed = process_for_output(df_filtered)
    
    # Export CSV
    df_processed.to_csv(args.output, index=False)
    print(f"\nExported {len(df_processed)} schools to CSV: {args.output}")
    
    # Summary
    print("\n--- Summary ---")
    if 'local_authority' in df_processed.columns:
        print("\nBy Borough:")
        print(df_processed['local_authority'].value_counts())
    
    if 'phase' in df_processed.columns:
        print("\nBy Phase:")
        print(df_processed['phase'].value_counts())
    
    # Export GeoJSON if requested
    if args.geojson:
        export_to_geojson(df_processed, args.geojson)
    
    print("\nDone!")


if __name__ == '__main__':
    main()