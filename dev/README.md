# Development Files

This folder contains development scripts and data files used during project development. These are **not required** for running the application but are kept for reference.

## Scripts

### Data Checking Scripts

- `check_hill_mead.py` - Verify Hill Mead Primary School data
- `check_laqn_data.py` - Test LAQN API connectivity
- `check_laqn_mismatch.py` - Debug LAQN sensor mismatches
- `check_schools_laqn.py` - Verify school-sensor relationships
- `check_sensor_fk.py` - Check sensor foreign key integrity
- `check_working_sensors.py` - Identify active sensors

### Data Processing Scripts

- `extract_laei_local.py` - Extract LAEI data for local area
- `process_schools.py` - Process raw school data into database format
- `db_snapshot.py` - Create database backup snapshots

## Data Files

### Processed Data

- `schools.geojson` - GeoJSON export of school locations
- `schools_processed.csv` - Cleaned school data
- `schools_with_laei.csv` - Schools with LAEI baseline data
- `schools_with_laei.json` - JSON version of school data
- `laei_summary.json` - Summary of LAEI data coverage

## Documentation

- `data_access_guide.md` - Internal guide for accessing various data sources

---

**Note:** These files are development artifacts and are not part of the deployed application.
