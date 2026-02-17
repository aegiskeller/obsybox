# NINA Target Finder for Eclipsing Binary Stars

Automated tool to scrape nightly minima predictions from var.astro.cz, filter targets based on observability criteria, and generate NINA-compatible JSON sequence files for automated imaging.

## Quick Start

```bash
# 1. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Launch the GUI (easiest method)
python target_selector_gui.py

# OR run command-line version
python findTargets.py

# 3. Import observation logs (after observing)
python parse_nina_log.py path/to/nina-log.log
```

## Features

- **Graphical User Interface**: Easy-to-use GUI with real-time validation and visual feedback
- **Automated Web Scraping**: Fetches eclipsing binary minima predictions from var.astro.cz
- **Smart Caching**: Caches daily predictions to avoid repeated requests
- **Coordinate Resolution**: Automatically fetches coordinates from var.astro.cz star pages with SIMBAD fallback
- **Altitude/Azimuth Filtering**: Only selects targets visible from your location
- **Dark Sky Awareness**: Schedules observations to start after astronomical twilight
- **Optimal Target Spacing**: Selects targets spaced 4 hours apart for efficient night coverage
- **Exposure Time Calculation**: Automatically calculates exposure times based on magnitude
- **Database Tracking**: Automatic tracking of scheduled and observed targets
  - Astronomical dating (noon-to-noon observing nights)
  - Multiple scheduling support with history tracking
  - Warning dialogs for already-observed targets
  - Log import and automatic observation matching
- **NINA Integration**: Generates complete NINA sequence files with:
  - MQTT notifications
  - Safety triggers (weather monitoring)
  - Autofocus, dithering, and guiding
  - Meridian flip handling
  - Automatic recovery procedures

## Requirements

**Python 3.11+** with a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

Required packages:
- selenium (web scraping)
- astropy (astronomical calculations)
- astroquery (coordinate lookups)
- beautifulsoup4 (HTML parsing)
- requests (HTTP requests)
- flask (optional, for web interface)
- pandas (optional, for data analysis)

**Note**: The GUI and command-line tools work best with the virtual environment activated. This avoids conflicts with system-installed packages (especially numpy/astropy).

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

### Method 1: Graphical User Interface (Recommended)

The easiest way to generate targets is using the GUI:

```bash
# Activate virtual environment
source venv/bin/activate

# Launch the GUI
python target_selector_gui.py
```

The GUI provides:
- **Visual Configuration**: Adjust all parameters with tooltips
- **Real-time Validation**: Instant feedback on invalid inputs
- **Pulsating Star Animation**: Visual progress indicator during target fetch
- **Target Preview**: See detailed target information before export
- **Database Recording on Export**: Targets are recorded when you export NINA JSON files
- **Export Options**: Generate NINA JSON files and CSV exports with one click

**Workflow:**
1. Adjust configuration parameters in the "Configuration" tab
2. Click "🎯 Generate Targets"
3. Review selected targets in the "Targets" tab
4. Click "💾 Export NINA JSON" to create NINA sequence files
5. **Targets are recorded in the database at this point** (when exporting)

### Method 2: Command-Line Interface

Run the script directly to generate tonight's targets:

```bash
# Activate virtual environment
source venv/bin/activate

# Generate targets
python findTargets.py
```

This will:
1. Scrape minima predictions for today (or load from cache)
2. Filter targets by magnitude, altitude, and azimuth
3. Select 2 optimal targets spaced throughout the night
4. Generate CSV/JSON exports with all filtered and selected targets
5. Create NINA sequence files for each selected target
6. **Note: Targets are NOT recorded in database** - use GUI for database tracking

**Note**: The command-line version generates files only. The GUI records targets in the database when you click "Export NINA JSON", allowing you to review targets before committing to the schedule.

### Output Files

The script generates several files:

- `targets_YYYY-MM-DD.csv` - All filtered targets for the night
- `targets_YYYY-MM-DD.json` - JSON version of all filtered targets
- `selected_targets_YYYY-MM-DD.csv` - The 2 selected optimal targets
- `selected_targets_YYYY-MM-DD.json` - JSON version of selected targets
- `<target_name>.json` - NINA sequence files (one per selected target)
- `cache_raw_targets_YYYY-MM-DD.json` - Cached scraping results
- `observations.sqlite` - Database tracking scheduled and observed targets

### Database Tracking

The system automatically tracks scheduled and observed targets in `observations.sqlite`:

#### Scheduling Targets
When targets are generated and exported, they are recorded in the database with:
- Target name, RA, Dec, constellation
- Magnitude range, variability type, minima type
- Scheduled date (`scheduled_for_night`)
- Scheduling timestamp (`scheduled_at`)
- Initially `observed_on` is NULL

**GUI**: Targets are recorded when you click "💾 Export NINA JSON" (allows review before scheduling)
**Command-line**: Targets are NOT recorded in database - use GUI for database tracking

#### Importing Observations
When you import NINA log files, the system:
- Parses exposure records with timestamps
- Uses astronomical dating (noon-to-noon observing nights)
- Updates `observed_on` for matching scheduled targets
- Marks exposures as scheduled in the log database

```bash
# Import a NINA log file using logexploit with proper database integration
cd ../logexploit
python -m logexploit --nina-integration --db ../nina_scheduling/observations.sqlite path/to/nina-log.log

# This creates proper foreign key relationships:
# - Links exposures to scheduled_targets
# - Updates observation_nights records
# - Stores in the observations table (not separate exposures table)
```

The parser will:
1. Extract exposure data (target, filter, datetime, etc.)
2. Calculate observation night (astronomical date)
3. Check for matching scheduled targets
4. Update database with observed dates

#### Re-scheduling Targets
If you schedule a target that has already been observed:
- A dialog box warns you the target was previously observed
- You can choose to proceed or cancel
- If you proceed, a **new entry** is created with:
  - Same `scheduled_for_night` date
  - Different `scheduled_at` timestamp
  - Separate `observed_on` status

This allows tracking:
- Targets scheduled multiple times
- Which scheduling attempt was actually observed
- Complete scheduling history

#### Querying the Database

```bash
# See all scheduled targets
sqlite3 observations.sqlite "SELECT * FROM nina_scheduled_targets ORDER BY scheduled_for_night DESC;"

# See targets scheduled but not observed
sqlite3 observations.sqlite "SELECT target_name, scheduled_for_night FROM nina_scheduled_targets WHERE observed_on IS NULL;"

# See targets scheduled multiple times
sqlite3 observations.sqlite < query_scheduling_history.sql

# See observation session details by night
sqlite3 observations.sqlite < scheduled_analysis_queries.sql
```

See `DATABASE_README.md`, `SCHEDULED_TARGETS_README.md`, and `LOG_TRACKING_README.md` for detailed database documentation.

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

### Core Scripts
- `findTargets.py` - Main script for target selection and NINA file generation
- `target_selector_gui.py` - Graphical user interface for target selection
- Use `logexploit` package (in ../logexploit/) - Parse NINA log files and import to database
- `exposure_time.py` - Exposure time calculation based on magnitude
- `observation_db.py` - Database utilities and helper functions

### Database
- `observations.sqlite` - Production database (scheduled and observed targets)
- `schema.sql` - Database schema definition
- `scheduled_analysis_queries.sql` - Pre-built analysis queries
- `query_scheduling_history.sql` - Query for targets scheduled multiple times

### Configuration & Templates
- `EN Gru.json` - Example NINA sequence file
- `G6432.00592.template.json` - Template for NINA JSON generation
- `profile_map.txt` - Maps NINA profile UUIDs to telescope names
- `requirements.txt` - Python dependencies
- `secrets.py` - MQTT/API credentials (not committed to git)

### Testing & Migration
- `test_already_observed.py` - Test dialog for already-observed targets
- `test_not_observed.py` - Test scheduling unobserved targets
- `test_future_schedule.py` - Test scheduling for future dates
- `test_reschedule.py` - Test rescheduling observed targets
- `test_log_import_update.py` - Test log import and database updates
- `migrate_scheduled_targets.py` - Database schema migration script
- `demo_dialog.py` - Interactive demo of scheduling dialogs

### Documentation
- `README.md` - This file
- `DATABASE_README.md` - Database structure and usage
- `SCHEDULED_TARGETS_README.md` - Scheduled targets tracking
- `LOG_TRACKING_README.md` - Log import and observation tracking

## Credits

Data source: [var.astro.cz](http://var.astro.cz) - Minima predictions for eclipsing binary stars

## License

See LICENSE file in repository root.
