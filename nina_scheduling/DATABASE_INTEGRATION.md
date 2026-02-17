# NINA Scheduling Database Integration

## Overview

The `logexploit` package now properly integrates with the NINA scheduling database using **foreign key relationships** instead of loose name-based coupling.

## Database Schema Integration

### Proper Foreign Key Chain

```
observation_nights (date_obs, telescope)
         ↓ (night_id FK)
      targets (target_name, coordinates, magnitudes, etc.)
         ↓ (target_id FK)
   scheduled_targets (links night + target + sequence)
         ↓ (scheduled_target_id FK)
    observations (individual FITS/XISF files with metadata)
```

### Tables and Relationships

#### 1. **observation_nights**
- One record per observing night (noon-to-noon)
- Fields: `date_obs`, `telescope`, `weather_conditions`, etc.
- Created by: `mark_targets_scheduled()` or NINA adapter

#### 2. **targets**
- Catalog of astronomical objects
- Fields: `target_name`, coordinates (RA/Dec), `magnitude_max/min`, `variability_type`, etc.
- Created by: `mark_targets_scheduled()` or NINA adapter

#### 3. **scheduled_targets**
- Links specific targets to specific nights
- Fields: `night_id` (FK), `target_id` (FK), `sequence_id` (FK), `status`, timing info
- Status values: `'planned'`, `'in_progress'`, `'completed'`, `'unscheduled'`, `'aborted'`
- Created by: `mark_targets_scheduled()` for scheduled observations
- Created by: NINA adapter for unscheduled/ad-hoc observations

#### 4. **observations**
- Individual exposure files (LIGHT frames)
- Fields: `scheduled_target_id` (FK), `file_path`, `exposure_time_sec`, `filter_name`, `datetime_start`, quality metrics, etc.
- Created by: NINA adapter when parsing logs with `--nina-integration`

## Usage Workflow

### 1. Schedule Targets (Before Observing)

```bash
cd nina_scheduling
python target_selector_gui.py
# Select targets and generate NINA sequences
```

This calls `mark_targets_scheduled()` which:
- Creates/finds `observation_nights` record for the date
- Creates/finds `targets` records for each object
- Creates `scheduled_targets` records linking them together (status='planned')

### 2. Observe with NINA

Run your NINA sequences, which creates log files.

### 3. Import Observations (After Observing)

```bash
cd logexploit
python -m logexploit --nina-integration --db ../nina_scheduling/observations.sqlite path/to/nina.log
```

The NINA adapter:
1. Parses the log file for exposures
2. Determines observation night (astronomical date)
3. Gets/creates `observation_nights` record
4. For each target:
   - Gets/creates `targets` catalog entry
   - Searches for matching `scheduled_targets` record
   - If found: Links to it (marks as 'completed')
   - If not found: Creates new `scheduled_targets` with status='unscheduled'
5. Stores each exposure in `observations` table with FK to `scheduled_targets`

## Querying the Integrated Data

### Find Scheduled vs. Actual Observations

```sql
SELECT 
    n.date_obs,
    t.target_name,
    st.status,
    COUNT(o.observation_id) AS exposure_count,
    SUM(o.exposure_time_sec) AS total_integration_time,
    MIN(o.datetime_start) AS first_exposure,
    MAX(o.datetime_start) AS last_exposure
FROM observation_nights n
JOIN scheduled_targets st ON n.night_id = st.night_id
JOIN targets t ON st.target_id = t.target_id
LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
WHERE n.date_obs = '2025-10-24'
GROUP BY n.date_obs, t.target_name, st.status
ORDER BY t.target_name;
```

### Find Targets That Were Scheduled But Not Observed

```sql
SELECT 
    n.date_obs,
    t.target_name,
    st.status,
    st.scheduled_start_time
FROM observation_nights n
JOIN scheduled_targets st ON n.night_id = st.night_id
JOIN targets t ON st.target_id = t.target_id
LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
WHERE n.date_obs = '2025-10-24'
  AND st.status = 'planned'
  AND o.observation_id IS NULL
ORDER BY st.scheduled_start_time;
```

### Find Ad-Hoc (Unscheduled) Observations

```sql
SELECT 
    t.target_name,
    COUNT(o.observation_id) AS exposure_count,
    MIN(o.datetime_start) AS first_exposure
FROM scheduled_targets st
JOIN targets t ON st.target_id = t.target_id
JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
WHERE st.status = 'unscheduled'
GROUP BY t.target_name;
```

### Observing Efficiency Analysis

```sql
WITH planned AS (
    SELECT COUNT(DISTINCT st.target_id) AS planned_targets
    FROM scheduled_targets st
    JOIN observation_nights n ON st.night_id = n.night_id
    WHERE n.date_obs = '2025-10-24' AND st.status = 'planned'
),
observed AS (
    SELECT COUNT(DISTINCT st.target_id) AS observed_targets
    FROM scheduled_targets st
    JOIN observation_nights n ON st.night_id = n.night_id
    JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
    WHERE n.date_obs = '2025-10-24' AND st.status IN ('completed', 'planned')
)
SELECT 
    planned.planned_targets,
    observed.observed_targets,
    ROUND(100.0 * observed.observed_targets / planned.planned_targets, 1) AS completion_percentage
FROM planned, observed;
```

## Benefits of Proper Integration

✅ **Referential Integrity**: Foreign keys prevent orphaned records  
✅ **Query Efficiency**: Indexed joins are faster than name matching  
✅ **Data Consistency**: Can't delete targets that have observations  
✅ **Clear Relationships**: Explicit links between scheduled and actual  
✅ **Status Tracking**: Know if target was planned, completed, or ad-hoc  
✅ **Multi-Night Support**: Same target can be scheduled across multiple nights  
✅ **Sequence Tracking**: Links back to which NINA sequence was used  

## Migration from Old System

If you have existing data in the old `nina_scheduled_targets` bridge table, you can migrate it:

```sql
-- This is handled automatically by the NINA adapter
-- It looks for matches in nina_scheduled_targets when creating scheduled_targets
```

The adapter is backward-compatible:
- Checks for old `nina_scheduled_targets` entries
- Creates proper `scheduled_targets` records with FKs
- Gradually migrates as you import new logs

## Command Reference

```bash
# Schedule targets (creates observation_nights, targets, scheduled_targets)
cd nina_scheduling
python findTargets.py --date 2025-10-24 --export

# Import observations with proper integration
cd ../logexploit
python -m logexploit --nina-integration \
    --db ../nina_scheduling/observations.sqlite \
    --telescope "SCT 8-inch" \
    path/to/nina-log.log

# Query the database
sqlite3 ../nina_scheduling/observations.sqlite < scheduled_analysis_queries.sql
```

## Architecture Comparison

### Before (Loose Coupling)
```
observations.sqlite
├─ sequences, observation_nights, targets, scheduled_targets, observations  (from schema)
├─ imaging_sessions, targets, exposures  (from logexploit - separate hierarchy)
└─ nina_scheduled_targets  (bridge table, name-based matching only)
```

### After (Proper Integration with --nina-integration)
```
observations.sqlite
├─ sequences                    (NINA sequence JSON files)
├─ observation_nights           (observing sessions, noon-to-noon)
├─ targets                      (catalog of astronomical objects)
├─ scheduled_targets            (links nights → targets → sequences)
└─ observations                 (individual FITS files with FK to scheduled_targets)
     ↑
     └─ Populated by logexploit --nina-integration
```

## See Also

- `schema.sql` - Full database schema definition
- `scheduled_analysis_queries.sql` - Pre-built analysis queries  
- `nina_adapter.py` - Implementation of NINA scheduling integration
