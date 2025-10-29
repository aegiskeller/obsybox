-- Scheduled Targets Analysis Queries
-- Example queries for analyzing scheduled vs actual observations
-- Note: Uses observation_night (astronomical date) not calendar date
--       Observation night runs from noon to noon (before midnight = previous calendar date)

-- 1. Schedule adherence summary by date
SELECT 
    st.scheduled_for_night,
    st.telescope,
    COUNT(DISTINCT st.target_name) as scheduled_targets,
    COUNT(DISTINCT CASE WHEN st.observed_on IS NOT NULL THEN st.target_name END) as observed_targets,
    ROUND(COUNT(DISTINCT CASE WHEN st.observed_on IS NOT NULL THEN st.target_name END) * 100.0 / COUNT(DISTINCT st.target_name), 1) as completion_rate
FROM nina_scheduled_targets st
GROUP BY st.scheduled_for_night, st.telescope
ORDER BY st.scheduled_for_night DESC;

-- 2. Scheduled targets that were successfully observed (on scheduled night)
SELECT 
    st.target_name,
    st.scheduled_for_night,
    st.observed_on,
    st.telescope,
    COUNT(le.id) as frames_taken,
    SUM(le.exposure_time) as total_exposure_seconds,
    COUNT(DISTINCT le.filter) as filters_used,
    MIN(le.exposure_datetime) as first_frame,
    MAX(le.exposure_datetime) as last_frame
FROM nina_scheduled_targets st
INNER JOIN nina_log_exposures le ON 
    st.target_name = le.target_name AND 
    le.observation_night = st.observed_on
WHERE st.observed_on = st.scheduled_for_night
GROUP BY st.target_name, st.scheduled_for_night, st.observed_on, st.telescope
ORDER BY st.scheduled_for_night DESC, frames_taken DESC;

-- 3. Scheduled targets that were observed on a DIFFERENT night (rescheduled)
SELECT 
    st.target_name,
    st.scheduled_for_night as originally_scheduled_for,
    st.observed_on as actually_observed_on,
    st.telescope,
    COUNT(le.id) as frames_taken
FROM nina_scheduled_targets st
INNER JOIN nina_log_exposures le ON 
    st.target_name = le.target_name AND 
    le.observation_night = st.observed_on
WHERE st.observed_on != st.scheduled_for_night
GROUP BY st.target_name, st.scheduled_for_night, st.observed_on, st.telescope
ORDER BY st.scheduled_for_night DESC;

-- 4. Scheduled targets that were NOT observed at all
SELECT 
    st.target_name,
    st.scheduled_for_night,
    st.telescope,
    st.scheduled_at
FROM nina_scheduled_targets st
WHERE st.observed_on IS NULL
ORDER BY st.scheduled_for_night DESC;

-- 5. Unscheduled observations (targets of opportunity)
SELECT 
    le.target_name,
    le.observation_night,
    le.telescope,
    COUNT(*) as frames_taken,
    SUM(le.exposure_time) as total_exposure_seconds,
    MIN(le.exposure_datetime) as first_frame,
    MAX(le.exposure_datetime) as last_frame
FROM nina_log_exposures le
WHERE le.target_name IS NOT NULL 
AND le.scheduled = 0
AND le.image_type = 'LIGHT'
GROUP BY le.target_name, le.observation_night, le.telescope
ORDER BY le.observation_night DESC, frames_taken DESC;

-- 6. Detailed exposure breakdown by target and schedule status
SELECT 
    le.target_name,
    le.observation_night,
    CASE WHEN le.scheduled = 1 THEN 'Scheduled' ELSE 'Unscheduled' END as status,
    le.filter,
    COUNT(*) as frame_count,
    SUM(le.exposure_time) as total_seconds,
    MIN(le.exposure_datetime) as first_frame,
    MAX(le.exposure_datetime) as last_frame
FROM nina_log_exposures le
WHERE le.target_name IS NOT NULL 
AND le.image_type = 'LIGHT'
GROUP BY le.target_name, le.observation_night, le.scheduled, le.filter
ORDER BY le.observation_night DESC, le.target_name, le.filter;

-- 7. Schedule vs actual comparison for a specific date
-- Replace '2025-10-24' with desired observation night
SELECT 
    COALESCE(st.target_name, le.target_name) as target_name,
    '2025-10-24' as observation_night,
    CASE 
        WHEN st.target_name IS NOT NULL THEN 'Yes' 
        ELSE 'No' 
    END as was_scheduled,
    CASE 
        WHEN le.target_name IS NOT NULL THEN 'Yes' 
        ELSE 'No' 
    END as was_observed,
    COALESCE(COUNT(le.id), 0) as frames_taken
FROM nina_scheduled_targets st
FULL OUTER JOIN nina_log_exposures le ON 
    st.target_name = le.target_name AND 
    st.scheduled_for_night = le.observation_night
WHERE st.scheduled_for_night = '2025-10-24'
OR le.observation_night = '2025-10-24'
GROUP BY COALESCE(st.target_name, le.target_name)
ORDER BY was_scheduled DESC, was_observed DESC;

-- 8. Monthly schedule adherence statistics
SELECT 
    strftime('%Y-%m', st.scheduled_for_night) as month,
    st.telescope,
    COUNT(DISTINCT st.target_name) as scheduled_targets,
    COUNT(DISTINCT CASE WHEN st.observed_on IS NOT NULL THEN st.target_name END) as completed_targets,
    ROUND(
        COUNT(DISTINCT CASE WHEN st.observed_on IS NOT NULL THEN st.target_name END) * 100.0 / 
        COUNT(DISTINCT st.target_name), 1
    ) as completion_rate
FROM nina_scheduled_targets st
GROUP BY strftime('%Y-%m', st.scheduled_for_night), st.telescope
ORDER BY month DESC;

-- 9. Observing session details by night
SELECT 
    observation_night,
    target_name,
    COUNT(*) as frames,
    COUNT(DISTINCT filter) as filters,
    SUM(exposure_time) as total_seconds,
    ROUND(SUM(exposure_time) / 60.0, 1) as total_minutes,
    MIN(exposure_datetime) as session_start,
    MAX(exposure_datetime) as session_end,
    ROUND((JULIANDAY(MAX(exposure_datetime)) - JULIANDAY(MIN(exposure_datetime))) * 24, 1) as session_hours
FROM nina_log_exposures
WHERE image_type = 'LIGHT' AND target_name IS NOT NULL
GROUP BY observation_night, target_name
ORDER BY observation_night DESC, session_start;
