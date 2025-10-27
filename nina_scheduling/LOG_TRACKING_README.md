# NINA Log File Tracking

The parse_nina_log.py script now tracks which log files have been imported to help manage multiple log files from the same observing night.

## Features

### 1. Automatic Log File Registration
Every imported log file is registered in the `nina_log_files` table with:
- Log filename and full path
- Telescope name (auto-detected from profile)
- Profile ID
- Observation date
- First and last exposure times
- Total exposure count
- Import timestamp

### 2. Exposure Tracking
Each exposure record includes a `log_file` column linking it back to the source log file.

### 3. Duplicate Detection
When re-importing a log file, the script warns you:
```
Note: This log file was previously imported on 2025-10-27 03:53:19
      (246 exposures). Duplicate exposures will be skipped.
```

## Database Schema

### nina_log_files Table
Tracks imported log files:
```sql
CREATE TABLE nina_log_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_filename TEXT NOT NULL UNIQUE,
    log_filepath TEXT NOT NULL,
    telescope TEXT,
    profile_id TEXT,
    observation_date DATE,
    first_exposure DATETIME,
    last_exposure DATETIME,
    exposure_count INTEGER,
    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### nina_log_exposures Table
Now includes `log_file` column:
```sql
CREATE TABLE nina_log_exposures (
    ...
    log_file TEXT,
    ...
)
```

## Usage

### Import Log Files
```bash
# Import with auto-detection
python parse_nina_log.py --log nina_log1.log --db obs.sqlite --profile-map profile_map.txt

# Import multiple files from same night
python parse_nina_log.py --log nina_log2.log --db obs.sqlite --profile-map profile_map.txt
python parse_nina_log.py --log nina_log3.log --db obs.sqlite --profile-map profile_map.txt
```

### Query Imported Log Files
```bash
# List all imported log files
python query_log_files.py obs.sqlite

# Filter by observation date
python query_log_files.py obs.sqlite --date 2025-10-24

# Filter by telescope
python query_log_files.py obs.sqlite --telescope "SCT 8-inch"
```

### SQL Queries

**List all log files for a specific night:**
```sql
SELECT log_filename, first_exposure, last_exposure, exposure_count
FROM nina_log_files
WHERE observation_date = '2025-10-24'
ORDER BY first_exposure;
```

**Count exposures by log file and type:**
```sql
SELECT 
    log_file,
    image_type,
    COUNT(*) as count
FROM nina_log_exposures
GROUP BY log_file, image_type
ORDER BY log_file, image_type;
```

**Find all exposures from a specific log file:**
```sql
SELECT exposure_datetime, image_type, target_name, filter, exposure_time
FROM nina_log_exposures
WHERE log_file = '20251024-143707-3.1.2.9001.3240-202510.log'
ORDER BY exposure_datetime;
```

**Get summary by observation date:**
```sql
SELECT 
    observation_date,
    COUNT(*) as log_file_count,
    SUM(exposure_count) as total_exposures
FROM nina_log_files
GROUP BY observation_date
ORDER BY observation_date DESC;
```

## Multiple Log Files per Night

NINA may create multiple log files during a single observing session (e.g., if NINA is restarted). The tracking system handles this by:

1. Each log file is registered separately
2. Exposures are linked to their source log file
3. You can query by observation_date to see all log files from a night
4. Duplicate exposures (same file path) are automatically skipped

## Example Workflow

```bash
# Import all log files from October 24, 2025
for log in 20251024*.log; do
    python parse_nina_log.py --log "$log" --db observations.sqlite --profile-map profile_map.txt
done

# Query what was imported
python query_log_files.py observations.sqlite --date 2025-10-24

# Output:
# Found 3 log file(s):
# 
# 📄 20251024-143707.log
#    Date: 2025-10-24
#    Time Range: 2025-10-24T19:29:26 to 2025-10-24T22:15:30
#    Exposures: 150
# 
# 📄 20251024-223045.log
#    Date: 2025-10-24
#    Time Range: 2025-10-24T22:31:15 to 2025-10-25T02:45:22
#    Exposures: 180
# 
# 📄 20251024-234512.log
#    Date: 2025-10-24
#    Time Range: 2025-10-25T02:46:00 to 2025-10-25T03:45:55
#    Exposures: 95
#
# Summary by Date:
#   2025-10-24: 3 log file(s), 425 exposures
```
