# Scheduled Targets Tracking

## Overview

The scheduled targets tracking system allows you to correlate which targets were scheduled for observation by `findTargets.py` with which targets were actually observed. This enables analysis of schedule adherence, target completion rates, and identification of unscheduled observations (targets of opportunity).

## Features

- **Automatic Recording**: `findTargets.py` automatically records scheduled targets when generating NINA JSON files
- **Date-Specific Tracking**: Targets are tracked per observation date (important for multi-night schedules)
- **Exposure Marking**: Individual exposures are marked as `scheduled=1` when they match a scheduled target
- **Historical Tracking**: Full history of what was scheduled vs. what was observed

## Database Schema

### `nina_scheduled_targets` Table

Tracks which targets were scheduled for observation:

```sql
CREATE TABLE nina_scheduled_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name TEXT NOT NULL,
    observation_date DATE NOT NULL,
    telescope TEXT,
    scheduled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_name, observation_date, telescope)
);
```

### `nina_log_exposures.scheduled` Column

Boolean flag (0 or 1) indicating whether an exposure was for a scheduled target:

```sql
ALTER TABLE nina_log_exposures ADD COLUMN scheduled BOOLEAN DEFAULT 0;
```

## Usage

### Automatic Scheduling (Recommended)

When `findTargets.py` generates target schedules, it automatically records them:

```bash
python findTargets.py --date 2025-10-24
```

This will:
1. Fetch minima predictions for the date
2. Select targets based on criteria
3. Export NINA JSON files
4. **Automatically record scheduled targets in the database**

### Manual Marking

You can also manually mark targets as scheduled using Python:

```python
from logexploit.database import mark_targets_scheduled

# Mark targets as scheduled for a specific date
targets = ['EG Scl', 'HX Eri', 'V* BV Cet']
observation_date = '2025-10-24'
telescope = 'SCT 8-inch'

marked = mark_targets_scheduled(
    db_path='observations.sqlite',
    targets=targets,
    observation_date=observation_date,
    telescope=telescope
)

print(f"Marked {marked} exposures as scheduled")
```

### Command-Line Marking

```bash
# Example: Mark targets as scheduled
python -c "
from logexploit.database import mark_targets_scheduled
targets = ['EG Scl', 'HX Eri']
marked = mark_targets_scheduled('observations.sqlite', targets, '2025-10-24', 'SCT 8-inch')
print(f'Marked {marked} exposures as scheduled')
"
```

## Analysis Queries

The `scheduled_analysis_queries.sql` file contains comprehensive queries for analyzing scheduled vs. actual observations. Here are some key examples:

### 1. Schedule Adherence Summary

Shows completion rate by date:

```sql
SELECT 
    st.observation_date,
    COUNT(DISTINCT st.target_name) as scheduled_targets,
    COUNT(DISTINCT le.target_name) as observed_targets,
    ROUND(COUNT(DISTINCT le.target_name) * 100.0 / COUNT(DISTINCT st.target_name), 1) as completion_rate
FROM nina_scheduled_targets st
LEFT JOIN nina_log_exposures le ON 
    st.target_name = le.target_name AND 
    DATE(le.exposure_datetime) = st.observation_date
GROUP BY st.observation_date
ORDER BY st.observation_date DESC;
```

### 2. Scheduled Targets That Were Observed

Details about successfully completed scheduled targets:

```sql
SELECT 
    st.target_name,
    st.observation_date,
    COUNT(le.id) as frames_taken,
    SUM(le.exposure_time) as total_exposure_seconds,
    COUNT(DISTINCT le.filter) as filters_used
FROM nina_scheduled_targets st
INNER JOIN nina_log_exposures le ON 
    st.target_name = le.target_name AND 
    DATE(le.exposure_datetime) = st.observation_date
GROUP BY st.target_name, st.observation_date
ORDER BY st.observation_date DESC;
```

### 3. Scheduled Targets That Were NOT Observed

Find what was planned but not executed:

```sql
SELECT 
    st.target_name,
    st.observation_date,
    st.telescope
FROM nina_scheduled_targets st
WHERE NOT EXISTS (
    SELECT 1 FROM nina_log_exposures le 
    WHERE le.target_name = st.target_name 
    AND DATE(le.exposure_datetime) = st.observation_date
)
ORDER BY st.observation_date DESC;
```

### 4. Unscheduled Observations (Targets of Opportunity)

Find targets that were observed but not scheduled:

```sql
SELECT 
    le.target_name,
    DATE(le.exposure_datetime) as observation_date,
    COUNT(*) as frames_taken,
    SUM(le.exposure_time) as total_exposure_seconds
FROM nina_log_exposures le
WHERE le.target_name IS NOT NULL 
AND le.scheduled = 0
AND le.image_type = 'LIGHT'
GROUP BY le.target_name, DATE(le.exposure_datetime)
ORDER BY observation_date DESC;
```

## Example Workflow

### 1. Schedule Targets for Tonight

```bash
# Generate schedule for tonight
python findTargets.py --date 2025-10-27

# This automatically:
# - Fetches predictions
# - Selects best targets
# - Exports NINA JSON files
# - Records scheduled targets in database
```

### 2. Observe During the Night

Use NINA to observe the scheduled targets. Log files are automatically generated.

### 3. Import Log Files

```bash
# Import log files from the night
python parse_nina_log.py \
    --log /path/to/nina/logs/20251027-*.log \
    --db observations.sqlite \
    --profile-map profile_map.txt
```

### 4. Analyze Results

```bash
# Check schedule adherence
sqlite3 -header -column observations.sqlite < scheduled_analysis_queries.sql

# Or run specific queries
sqlite3 -header -column observations.sqlite "
SELECT target_name, COUNT(*) as frames 
FROM nina_log_exposures 
WHERE scheduled = 1 
AND DATE(exposure_datetime) = '2025-10-27'
GROUP BY target_name;
"
```

## Understanding the Results

### Scheduled Flag Values

- **`scheduled = 1`**: Exposure was for a target that was scheduled for that observation date
- **`scheduled = 0`**: Exposure was either:
  - For an unscheduled target (target of opportunity)
  - For a scheduled target but on a different date
  - A calibration frame (BIAS/FLAT/DARK)

### Date Specificity

The system is date-specific. If you schedule "EG Scl" for 2025-10-24 and observe it on 2025-10-25, those exposures will be marked as `scheduled = 0` because they don't match the scheduled date.

To mark them as scheduled:

```python
mark_targets_scheduled('observations.sqlite', ['EG Scl'], '2025-10-25', 'SCT 8-inch')
```

### Partial Observations

A target may be scheduled but only partially observed (e.g., only some filters completed). Query #8 in `scheduled_analysis_queries.sql` helps identify these cases.

## Common Scenarios

### Scenario 1: Perfect Adherence

- Scheduled: EG Scl, HX Eri, V* BV Cet
- Observed: EG Scl (50 frames), HX Eri (40 frames), V* BV Cet (60 frames)
- Result: 100% completion rate, all exposures marked `scheduled = 1`

### Scenario 2: Partial Completion

- Scheduled: EG Scl, HX Eri, V* BV Cet
- Observed: EG Scl (50 frames), HX Eri (40 frames)
- Result: 67% completion rate, V* BV Cet shows in "not observed" query

### Scenario 3: Targets of Opportunity

- Scheduled: EG Scl, HX Eri
- Observed: EG Scl (50 frames), HX Eri (40 frames), V* TW Psc (30 frames)
- Result: V* TW Psc shows as unscheduled (`scheduled = 0`)

### Scenario 4: Weather Delay

- Scheduled: EG Scl for 2025-10-24
- Observed: EG Scl on 2025-10-25 (weather delay)
- Result: Exposures marked `scheduled = 0` unless manually updated for new date

## Troubleshooting

### "Marked 0 exposures as scheduled"

This happens when:
1. **No matching exposures exist**: Import log files first with `parse_nina_log.py`
2. **Date mismatch**: Check that observation_date matches the DATE() of exposure_datetime
3. **Name mismatch**: Ensure target names match exactly (case-sensitive)

### Check actual observation dates:

```sql
SELECT target_name, DATE(exposure_datetime), COUNT(*) 
FROM nina_log_exposures 
WHERE target_name = 'Your Target'
GROUP BY target_name, DATE(exposure_datetime);
```

### Targets Not Being Recorded

Check that `findTargets.py` is calling `record_scheduled_targets()`:

```python
# Should be in main block of findTargets.py
if selected:
    export_to_nina_json(selected)
    record_scheduled_targets(selected, date.today())  # This line
```

### Database Path Issues

`findTargets.py` looks for the database in the same directory. To specify a different path:

```python
# In findTargets.py
record_scheduled_targets(selected, date.today(), db_path='/path/to/observations.sqlite')
```

## Best Practices

1. **Import logs regularly**: Import log files after each observing session for timely analysis
2. **Use consistent target names**: Ensure target names in findTargets.py match those in NINA
3. **Review unscheduled observations**: Check for interesting targets of opportunity
4. **Track completion rates**: Monitor schedule adherence over time to optimize planning
5. **Document weather/technical issues**: Note in separate system when scheduled targets couldn't be observed

## Integration with Other Tools

### query_log_files.py

The query utility can show scheduled targets for a date:

```bash
python query_log_files.py --date 2025-10-27 --show-scheduled
```

### Future Enhancements

Potential additions:
- Web dashboard showing schedule vs. actual
- Automatic scheduling adjustment based on completion history
- Integration with weather data for non-completion analysis
- Email/notification for schedule adherence reports

## Technical Details

### Atomicity

The `mark_targets_scheduled()` function updates both tables in a single transaction:

```python
def mark_targets_scheduled(db_path, targets, observation_date, telescope=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        for target in targets:
            # Insert into scheduled_targets
            cursor.execute('''INSERT OR IGNORE INTO nina_scheduled_targets ...''')
            
            # Update exposures
            cursor.execute('''UPDATE nina_log_exposures SET scheduled = 1 ...''')
        
        conn.commit()  # Atomic commit
    except Exception as e:
        conn.rollback()
        raise
```

### Performance

For large databases, consider adding indices:

```sql
CREATE INDEX idx_exposures_scheduled ON nina_log_exposures(scheduled);
CREATE INDEX idx_exposures_target_date ON nina_log_exposures(target_name, exposure_datetime);
CREATE INDEX idx_scheduled_date ON nina_scheduled_targets(observation_date);
```

## See Also

- `LOG_TRACKING_README.md`: Documentation on log file tracking
- `DATABASE_README.md`: Database schema and structure
- `scheduled_analysis_queries.sql`: Pre-built analysis queries
- `../logexploit/`: NINA log parser package for importing observations
