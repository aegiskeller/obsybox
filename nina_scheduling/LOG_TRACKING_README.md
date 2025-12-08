# NINA Log File Tracking

**Note: This functionality is now provided by the `logexploit` package in `../logexploit/`.**

The logexploit package tracks which log files have been imported to help manage multiple log files from the same observing night.

## Features

### 1. Automatic Log File Registration
Every imported log file is registered in the database with:
- Log filename and full path
- Session start and end times
- Target count
- Total exposure count
- Import timestamp

### 2. Exposure Tracking
Each exposure record is linked to its target and session.

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
# Import a NINA log file using logexploit
# IMPORTANT: Use the shared observations.sqlite database
cd ../logexploit
python -m logexploit --db ../nina_scheduling/observations.sqlite nina_log.log

# The log will be stored in the shared database
# This allows mark_targets_scheduled() to link exposures to scheduled targets
# Subsequent imports of the same file will be detected and skipped
```

### Query Imported Sessions
```bash
# List all imported sessions (use logexploit's web UI with shared database)
cd ../logexploit
python -m logexploit --db ../nina_scheduling/observations.sqlite --ui

# Or use the CLI to list sessions
python -m logexploit --db ../nina_scheduling/observations.sqlite --list-sessions

# Show details for a specific session
python -m logexploit --db ../nina_scheduling/observations.sqlite --show-session 1
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

1. Each log file is registered separately as a session
2. Exposures are linked to their targets and sessions
3. You can query by date to see all sessions from a night
4. Duplicate log files (same file and modification time) are automatically skipped

## Example Workflow

```bash
# Import all log files from October 24, 2025
cd ../logexploit
DB_PATH="../nina_scheduling/observations.sqlite"
for log in /path/to/logs/20251024*.log; do
    python -m logexploit --db "$DB_PATH" "$log"
done

# View imported sessions in web UI
python -m logexploit --db "$DB_PATH" --ui

# Or list sessions via CLI
python -m logexploit --list-sessions

# Example output:
# Session 1: nina_log_20251024.log
#   Date: 2025-10-24 19:29 to 22:15
#   Targets: 5
#   Exposures: 150
# 
# Session 2: nina_log_20251024_part2.log
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
