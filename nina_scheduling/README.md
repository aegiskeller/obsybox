# NINA Target Finder for Eclipsing Binary Stars

Automated tool to scrape nightly minima predictions from var.astro.cz, filter targets based on observability criteria, and generate NINA-compatible JSON sequence files for automated imaging.

## Features

- **Automated Web Scraping**: Fetches eclipsing binary minima predictions from var.astro.cz
- **Smart Caching**: Caches daily predictions to avoid repeated requests
- **Coordinate Resolution**: Automatically fetches coordinates from var.astro.cz star pages with SIMBAD fallback
- **Altitude/Azimuth Filtering**: Only selects targets visible from your location
- **Dark Sky Awareness**: Schedules observations to start after astronomical twilight
- **Optimal Target Spacing**: Selects targets spaced 4 hours apart for efficient night coverage
- **Exposure Time Calculation**: Automatically calculates exposure times based on magnitude
- **NINA Integration**: Generates complete NINA sequence files with:
  - MQTT notifications
  - Safety triggers (weather monitoring)
  - Autofocus, dithering, and guiding
  - Meridian flip handling
  - Automatic recovery procedures

## Requirements

```bash
pip install -r requirements.txt
```

Required packages:
- selenium
- astropy
- astroquery
- python-dateutil

## Configuration

Edit the configuration section at the top of `findTargets.py`:

```python
OBSERVER_LOCATION = {
    'latitude': -31.27,    # Your observatory latitude
    'longitude': 149.62,   # Your observatory longitude
    'elevation': 300.0,    # Elevation in meters
    'timezone': 'Australia/Sydney'
}

# Target selection criteria
MIN_ALTITUDE = 30.0        # Minimum altitude (degrees)
MAX_ALTITUDE = 85.0        # Maximum altitude (degrees)
MIN_AZIMUTH = 60.0         # Minimum azimuth (degrees)
MAX_AZIMUTH = 300.0        # Maximum azimuth (degrees)
MAX_MAGNITUDE = 13.5       # Faintest magnitude to consider
MIN_DECLINATION = -40.0    # Minimum declination (degrees)
MAX_DECLINATION = 0.0      # Maximum declination (degrees)
DARK_SKY_ALTITUDE = -15.0  # Sun altitude for dark sky (degrees)

# NINA template configuration
NINA_TEMPLATE_FILE = "G6432.00592.template.json"  # Template file for NINA JSON generation
```

### Using Custom Templates

The script uses a template file to generate NINA sequence files. This makes it easy to customize the generated sequences:

1. **Default Template**: `G6432.00592.template.json` includes:
   - MQTT notifications
   - Pushover notifications
   - Safety monitoring (weather)
   - Autofocus, dithering, and guiding
   - Meridian flip handling
   - Automatic recovery procedures

2. **Creating Custom Templates**:
   - Create your own template in NINA
   - Export it to JSON
   - Save it in the `nina_scheduling` directory
   - Update `NINA_TEMPLATE_FILE` in `findTargets.py`

3. **Template Fields Updated Automatically**:
   - Target name
   - RA/Dec coordinates (all instances)
   - Observation start time
   - Exposure time

All other sequence settings (filters, binning, triggers, safety procedures, etc.) come from your template file.

## Usage

### Basic Usage

Run the script to generate tonight's targets:

```bash
python findTargets.py
```

This will:
1. Scrape minima predictions for today (or load from cache)
2. Filter targets by magnitude, altitude, and azimuth
3. Select 2 optimal targets spaced throughout the night
4. Generate CSV/JSON exports with all filtered and selected targets
5. Create NINA sequence files for each selected target

### Output Files

The script generates several files:

- `targets_YYYY-MM-DD.csv` - All filtered targets for the night
- `targets_YYYY-MM-DD.json` - JSON version of all filtered targets
- `selected_targets_YYYY-MM-DD.csv` - The 2 selected optimal targets
- `selected_targets_YYYY-MM-DD.json` - JSON version of selected targets
- `<target_name>.json` - NINA sequence files (one per selected target)
- `cache_raw_targets_YYYY-MM-DD.json` - Cached scraping results

### Importing into NINA

1. Run `python findTargets.py` to generate target files
2. Open NINA and go to the Advanced Sequencer
3. Click "Load Target Set" or "Import Target"
4. Select one of the generated JSON files (e.g., `G8482.00208.json`)
5. The complete sequence will be loaded with all triggers and safety procedures

### Manual Target Selection

You can also regenerate NINA files from a previously saved selection:

```python
from findTargets import export_to_nina_json
import json

# Load previously selected targets
with open('selected_targets_2025-10-26.json', 'r') as f:
    targets = json.load(f)

# Regenerate NINA files
export_to_nina_json(targets)
```

## Target Selection Logic

1. **Initial Filtering**: Removes targets that don't meet magnitude, altitude, or azimuth criteria
2. **Declination Filtering**: Removes targets outside the declination range (applied during coordinate lookup)
3. **Dark Sky Calculation**: Determines when astronomical twilight ends (sun at -15°)
4. **Two-Hour Window**: Only considers targets with minima ±1 hour from observation time
5. **Optimal Spacing**: Selects 2 targets spaced ~4 hours apart, starting after dark sky
6. **Coordinate Verification**: Fetches precise coordinates for selected targets
7. **Detailed Validation**: Performs detailed altitude checks for final selection

## Coordinate Resolution

The script uses a two-stage approach:
1. **Primary**: Scrapes coordinates from var.astro.cz star detail pages
2. **Fallback**: Queries SIMBAD if var.astro.cz lookup fails

## NINA Sequence Structure

Each generated NINA file includes:
- **Target Information**: Name, coordinates, rotation angle
- **Smart Exposure**: Calculated exposure time based on magnitude
- **Imaging Sequence**: 100 exposures with dithering every 5 frames
- **Safety Monitoring**: Automatic pause/resume on weather alerts
- **Autofocus**: Triggers on HFR increase and temperature change
- **Guiding**: PHD2 integration with auto-restart
- **Meridian Flip**: Automatic handling with recenter and guide resume
- **MQTT Notifications**: Publishes target info to MQTT broker

## Troubleshooting

### Script won't run
- Ensure you're in the correct Python environment
- Install dependencies: `pip install -r requirements.txt`
- Check that selenium and chromedriver are properly installed

### No targets found
- Verify your location coordinates are correct
- Check altitude/azimuth limits aren't too restrictive
- Confirm there are eclipsing binaries visible from your location tonight

### NINA import fails
- Ensure NINA is up to date
- Check that the JSON file is valid (not corrupted)
- Verify all NINA plugins are installed (PHD2, safety monitor, etc.)

### Coordinates not found
- The script will try SIMBAD as a fallback
- Some new variables may not have coordinates in either database
- You can manually add coordinates to the JSON file if needed

## Files in this Directory

- `findTargets.py` - Main script for target selection and NINA file generation
- `exposure_time.py` - Exposure time calculation based on magnitude
- `EN Gru.json` - Template NINA sequence file
- `requirements.txt` - Python dependencies
- `secrets.py` - MQTT credentials (not committed to git)

## Credits

Data source: [var.astro.cz](http://var.astro.cz) - Minima predictions for eclipsing binary stars

## License

See LICENSE file in repository root.
