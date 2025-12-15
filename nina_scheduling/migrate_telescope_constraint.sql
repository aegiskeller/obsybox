-- Migration to allow multiple telescopes per observation night
-- Changes UNIQUE constraint from (date_obs) to (date_obs, telescope)

BEGIN TRANSACTION;

-- Drop views that depend on observation_nights
DROP VIEW IF EXISTS v_night_targets;
DROP VIEW IF EXISTS v_observations_summary;
DROP VIEW IF EXISTS v_nightly_statistics;
DROP VIEW IF EXISTS v_target_history;

-- Recreate observation_nights with composite UNIQUE constraint
CREATE TABLE observation_nights_new (
    night_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_obs DATE NOT NULL,
    telescope TEXT,
    observer TEXT,
    weather_conditions TEXT,
    seeing_arcsec REAL,
    dark_sky_start TIME,
    dark_sky_end TIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(date_obs, telescope)
);

-- Copy existing data
INSERT INTO observation_nights_new SELECT * FROM observation_nights;

-- Replace old table
DROP TABLE observation_nights;
ALTER TABLE observation_nights_new RENAME TO observation_nights;

-- Recreate index
CREATE INDEX idx_obs_nights_date ON observation_nights(date_obs);

-- Recreate views
CREATE VIEW v_night_targets AS
SELECT
    n.date_obs,
    n.telescope,
    t.target_name,
    t.constellation,
    t.magnitude_max,
    t.variability_type,
    st.scheduled_start_time,
    st.scheduled_end_time,
    st.minima_time,
    st.status,
    st.images_captured,
    st.images_kept,
    s.sequence_name,
    st.scheduled_target_id
FROM scheduled_targets st
JOIN observation_nights n ON st.night_id = n.night_id
JOIN targets t ON st.target_id = t.target_id
LEFT JOIN sequences s ON st.sequence_id = s.sequence_id
ORDER BY n.date_obs DESC, st.scheduled_start_time;

CREATE VIEW v_observations_summary AS
SELECT
    o.observation_id,
    o.file_name,
    n.date_obs,
    t.target_name,
    o.datetime_start,
    o.exposure_time_sec,
    o.filter_name,
    o.fwhm_arcsec,
    o.hfr,
    o.quality_flag,
    o.calibrated,
    o.processed,
    st.status as target_status
FROM observations o
JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id
JOIN targets t ON st.target_id = t.target_id
JOIN observation_nights n ON st.night_id = n.night_id
ORDER BY o.datetime_start DESC;

CREATE VIEW v_nightly_statistics AS
SELECT
    n.date_obs,
    n.telescope,
    COUNT(DISTINCT st.scheduled_target_id) as num_targets_scheduled,
    COUNT(DISTINCT CASE WHEN st.status = 'completed' THEN st.scheduled_target_id END) as num_targets_completed,
    SUM(st.images_captured) as total_images,
    SUM(st.images_kept) as total_images_kept,
    AVG(st.average_fwhm) as avg_fwhm,
    MIN(st.actual_start_time) as first_image_time,
    MAX(st.actual_end_time) as last_image_time
FROM observation_nights n
LEFT JOIN scheduled_targets st ON n.night_id = st.night_id
GROUP BY n.night_id, n.date_obs, n.telescope
ORDER BY n.date_obs DESC;

CREATE VIEW v_target_history AS
SELECT
    t.target_name,
    t.constellation,
    t.variability_type,
    COUNT(DISTINCT n.night_id) as nights_observed,
    COUNT(o.observation_id) as total_observations,
    MIN(n.date_obs) as first_observed,
    MAX(n.date_obs) as last_observed,
    AVG(o.fwhm_arcsec) as avg_fwhm,
    AVG(o.airmass) as avg_airmass
FROM targets t
LEFT JOIN scheduled_targets st ON t.target_id = st.target_id
LEFT JOIN observation_nights n ON st.night_id = n.night_id
LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
GROUP BY t.target_id, t.target_name, t.constellation, t.variability_type;

COMMIT;
