# Observation Database Schema

This database schema provides a comprehensive system for managing astronomical observations with NINA (Nighttime Imaging 'N' Astronomy).

## Overview

The database models the complete observation workflow:

1. **Sequences** → NINA sequence files (.json) that define how to observe targets
2. **Observation Nights** → Individual nights with weather, telescope, and timing info
3. **Targets** → Astronomical objects (variable stars, asteroids, etc.) with coordinates
4. **Scheduled Targets** → Targets scheduled for specific nights using specific sequences
5. **Observations** → Individual image captures with full metadata
6. **Photometry** → Photometric measurements and light curves

## Entity Relationships

```
sequences (reusable)
    ↓
scheduled_targets ← observation_nights
    ↑                       ↑
targets              (date, telescope)
    ↓
observations (LIGHT frames)
    ↓
photometry (measurements)
```

## Core Tables

### sequences
NINA sequence files that can be used across multiple nights.

**Key fields:**
- `sequence_name`: e.g., "G6432.00592", "EN Gru"
- `sequence_file_path`: Full path to .json file
- `template_used`: Which template was used to generate it

**Usage:** A sequence like "G6432.00592.json" can be used on multiple nights for the same target.

### observation_nights
Individual observation nights with metadata.

**Key fields:**
- `date_obs`: Observation date (YYYY-MM-DD)
- `telescope`: Telescope identifier ("SCT", "RC", etc.)
- `dark_sky_start/end`: When dark sky observation window was
- `weather_conditions`, `seeing_arcsec`: Environmental data

**Usage:** One row per night. Links to multiple scheduled_targets.

### targets
Astronomical objects with coordinates and properties.

**Key fields:**
- `target_name`: Unique identifier (e.g., "G6432.00592")
- `target_type`: "variable_star", "asteroid", "exoplanet", etc.
- `ra_hours`, `ra_minutes`, `ra_seconds`: RA (J2000)
- `dec_degrees`, `dec_minutes`, `dec_seconds`, `dec_negative`: Dec (J2000)
- `magnitude_max/min`: Brightness range
- `variability_type`: "EA", "EB", "EW", etc.
- `period_days`: Orbital/pulsation period

**Usage:** One row per unique target. Can be observed many times.

### scheduled_targets
Links targets to specific nights, tracking what was scheduled and executed.

**Key fields:**
- `night_id`, `target_id`, `sequence_id`: Foreign keys
- `scheduled_start_time`, `scheduled_end_time`: Planned times (UTC)
- `minima_time`: Expected minima for variables (UTC)
- `observation_window_hours`: Planned duration
- `actual_start_time`, `actual_end_time`: When it really happened
- `status`: 'planned', 'in_progress', 'completed', 'aborted', 'failed'
- `images_captured`, `images_kept`: Statistics
- `average_fwhm`, `average_hfr`: Quality metrics

**Usage:** Each time you schedule a target for a night, create one row here.

### observations
Individual image captures (LIGHT frames) with complete metadata.

**Key fields:**
- `scheduled_target_id`: Links to the scheduled target
- `file_path`: Full path to FITS/XISF file
- `exposure_time_sec`, `filter_name`, `binning`, `gain`, `offset`
- `datetime_start`, `datetime_end`, `julian_date`
- `fwhm_arcsec`, `hfr`, `stars_detected`: Image quality
- `telescope_ra/dec/alt/az`, `airmass`: Telescope state
- `guiding_rms_arcsec`: Guiding performance
- `temperature_c`, `humidity_percent`: Environmental
- `calibrated`, `plate_solved`, `processed`: Processing status
- `quality_flag`: 'good', 'acceptable', 'poor', 'rejected'
- `included_in_analysis`: Boolean flag

**Usage:** One row per FITS/XISF file captured.

### photometry
Photometric measurements from processed observations.

**Key fields:**
- `observation_id`: Links to specific observation
- `aperture_radius_pixels`, `annulus_inner/outer_radius_pixels`
- `instrumental_magnitude`, `magnitude_error`
- `calibrated_magnitude`: After comparison star calibration
- `snr`: Signal-to-noise ratio
- `comp_star_1/2_mag`: Comparison star magnitudes

**Usage:** One or more rows per observation if multiple apertures tested.

## Utility Tables

### observation_metadata
Flexible key-value store for FITS headers and other properties.

### calibration_frames
Master calibration files (bias, dark, flat) used.

### observation_calibrations
Links observations to the calibration frames applied.

## Views

### v_night_targets
Complete view of all targets scheduled for each night with status.

### v_observations_summary
Quick summary of observations with target info, date, quality.

### v_nightly_statistics
Aggregate statistics per night (how many targets, images, quality metrics).

### v_target_history
Historical summary for each target (how many nights observed, quality trends).

## Example Usage

### Python API

```python
from observation_db import ObservationDB

db = ObservationDB("observations.sqlite")

# Add a target
target_id = db.add_target(
    target_name="G6432.00592",
    target_type="variable_star",
    ra_hours=0, ra_minutes=42, ra_seconds=33.41,
    dec_degrees=-38, dec_minutes=50, dec_seconds=59.5,
    dec_negative=True,
    constellation="Scl",
    magnitude_max=11.98,
    magnitude_min=12.5,
    variability_type="EA"
)

# Add an observation night
night_id = db.add_night(
    date_obs="2025-10-27",
    telescope="SCT",
    observer="John Doe",
    seeing_arcsec=2.5
)

# Schedule the target for this night
scheduled_id = db.schedule_target(
    night_id=night_id,
    target_id=target_id,
    scheduled_start_time="2025-10-27T09:36:00",
    scheduled_end_time="2025-10-27T13:36:00",
    observation_window_hours=4.0
)

# Add an observation (image capture)
obs_id = db.add_observation(
    scheduled_target_id=scheduled_id,
    file_path="/data/2025-10-27/LIGHT/G6432.00592/image_001.fits",
    file_name="image_001.fits",
    exposure_time_sec=51.0,
    filter_name="L",
    binning="1x1",
    datetime_start="2025-10-27T09:45:30",
    fwhm_arcsec=2.1,
    hfr=2.8,
    quality_flag="good"
)

# Get nightly summary
summary = db.get_nightly_summary("2025-10-27")
print(f"Targets: {summary['num_targets_scheduled']}")
print(f"Images: {summary['total_images']}")
```

### Command Line

```bash
# Initialize database
python observation_db.py --init --db observations.sqlite

# Scan for LIGHT directories and import
python observation_db.py --scan D:\ --telescope SCT --db observations.sqlite

# Get summary for a specific night
python observation_db.py --summary 2025-10-27 --db observations.sqlite

# Dry run (see what would be imported)
python find_light_subdirs.py --base-path D:\ --dry-run
```

## SQL Queries

### Get all targets observed on a specific night
```sql
SELECT t.target_name, st.scheduled_start_time, st.images_captured, st.status
FROM scheduled_targets st
JOIN targets t ON st.target_id = t.target_id
JOIN observation_nights n ON st.night_id = n.night_id
WHERE n.date_obs = '2025-10-27'
ORDER BY st.scheduled_start_time;
```

### Get observation history for a target
```sql
SELECT n.date_obs, COUNT(o.observation_id) as num_images, 
       AVG(o.fwhm_arcsec) as avg_fwhm
FROM observations o
JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id
JOIN targets t ON st.target_id = t.target_id
JOIN observation_nights n ON st.night_id = n.night_id
WHERE t.target_name = 'G6432.00592'
GROUP BY n.date_obs
ORDER BY n.date_obs;
```

### Find best quality images
```sql
SELECT o.file_name, o.datetime_start, o.fwhm_arcsec, o.hfr, t.target_name
FROM observations o
JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id
JOIN targets t ON st.target_id = t.target_id
WHERE o.quality_flag = 'good' 
  AND o.fwhm_arcsec < 2.5
  AND o.included_in_analysis = 1
ORDER BY o.fwhm_arcsec
LIMIT 100;
```

## Integration with NINA

The schema is designed to integrate with NINA workflows:

1. **Target Selection**: Generate NINA sequences using `findTargets.py`
2. **Sequence Storage**: Store sequence files in `sequences` table
3. **Nightly Planning**: Create `observation_nights` and `scheduled_targets` entries
4. **Execution**: NINA executes sequences, captures images
5. **Import**: Scan LIGHT directories with `find_light_subdirs.py`
6. **Analysis**: Query observations for photometry, quality assessment

## File Paths

- `schema.sql`: Complete database schema
- `observation_db.py`: Python API for database operations
- `find_light_subdirs.py`: Scanner for importing LIGHT directories
- `observations.sqlite`: Default database file (created automatically)

## Best Practices

1. **Use sequences table**: Track which sequence files you used
2. **Record actual times**: Update `actual_start_time`/`actual_end_time` in scheduled_targets
3. **Set quality flags**: Mark bad images so they're excluded from analysis
4. **Include metadata**: Use observation_metadata for custom FITS headers
5. **Track calibrations**: Link observations to calibration frames used
6. **Regular backups**: SQLite database is a single file - easy to backup

## Migration from Old Schema

The old schema had a simple `observations` table with:
- `target`, `dateobs`, `telescope`, `processed`

To migrate:
1. Targets → targets table (target becomes target_name)
2. dateobs → observation_nights table
3. Create scheduled_targets entries linking them
4. Keep processed field in observations table

Migration script coming soon.
