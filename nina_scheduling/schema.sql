-- Astronomical Observation Database Schema
-- Manages sequence files, observation nights, targets, and image captures

-- ============================================================================
-- SEQUENCES: NINA sequence files that can be used across multiple nights
-- ============================================================================
CREATE TABLE IF NOT EXISTS sequences (
    sequence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_name TEXT NOT NULL UNIQUE,  -- e.g., "G6432.00592", "EN Gru"
    sequence_file_path TEXT,              -- Full path to .json file
    template_used TEXT,                   -- Template file it was based on
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- OBSERVATION NIGHTS: Individual nights of observation
-- ============================================================================
CREATE TABLE IF NOT EXISTS observation_nights (
    night_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_obs DATE NOT NULL UNIQUE,        -- Observation date (YYYY-MM-DD)
    telescope TEXT,                        -- Telescope identifier (e.g., "SCT", "RC")
    observer TEXT,                         -- Observer name
    weather_conditions TEXT,               -- Weather notes
    seeing_arcsec REAL,                    -- Seeing in arcseconds
    dark_sky_start TIME,                   -- When dark sky began (local time)
    dark_sky_end TIME,                     -- When dark sky ended (local time)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- TARGETS: Astronomical objects (variables, asteroids, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS targets (
    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_name TEXT NOT NULL UNIQUE,     -- e.g., "G6432.00592", "EN Gru"
    target_type TEXT,                      -- e.g., "variable_star", "asteroid", "exoplanet"
    
    -- Coordinates (J2000)
    ra_hours INTEGER,
    ra_minutes INTEGER,
    ra_seconds REAL,
    dec_degrees INTEGER,
    dec_minutes INTEGER,
    dec_seconds REAL,
    dec_negative BOOLEAN,
    
    -- Additional target properties
    constellation TEXT,
    magnitude_max REAL,
    magnitude_min REAL,
    variability_type TEXT,                -- e.g., "EA", "EB", "EW"
    period_days REAL,                     -- Period in days
    
    -- Source information
    catalog_id TEXT,                      -- e.g., "VSX J123456.7+123456"
    gcvs_name TEXT,
    wds_identifier TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- SCHEDULED TARGETS: Targets scheduled for a specific night
-- Links observation nights to targets via sequences
-- ============================================================================
CREATE TABLE IF NOT EXISTS scheduled_targets (
    scheduled_target_id INTEGER PRIMARY KEY AUTOINCREMENT,
    night_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    sequence_id INTEGER,                   -- Which sequence file was used
    
    -- Scheduling information
    scheduled_start_time DATETIME,         -- UTC
    scheduled_end_time DATETIME,           -- UTC
    minima_time DATETIME,                  -- Expected minima time (UTC)
    
    -- Observation window
    observation_window_hours REAL,         -- Planned observation duration
    actual_start_time DATETIME,            -- When observation actually started
    actual_end_time DATETIME,              -- When observation actually ended
    
    -- Execution status
    status TEXT DEFAULT 'planned',         -- 'planned', 'in_progress', 'completed', 'aborted', 'failed'
    completion_percentage REAL,            -- 0-100
    
    -- Quality metrics
    images_captured INTEGER DEFAULT 0,
    images_kept INTEGER DEFAULT 0,
    average_fwhm REAL,                     -- Average FWHM in arcseconds
    average_hfr REAL,                      -- Average HFR
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (night_id) REFERENCES observation_nights(night_id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES targets(target_id) ON DELETE CASCADE,
    FOREIGN KEY (sequence_id) REFERENCES sequences(sequence_id) ON DELETE SET NULL,
    UNIQUE(night_id, target_id, scheduled_start_time)
);

-- ============================================================================
-- OBSERVATIONS: Individual image captures (LIGHT frames)
-- ============================================================================
CREATE TABLE IF NOT EXISTS observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheduled_target_id INTEGER NOT NULL,
    
    -- File information
    file_path TEXT NOT NULL UNIQUE,        -- Full path to FITS/XISF file
    file_name TEXT NOT NULL,
    file_size_bytes INTEGER,
    file_format TEXT,                      -- 'FITS', 'XISF', etc.
    
    -- Observation parameters
    exposure_time_sec REAL NOT NULL,
    filter_name TEXT,                      -- 'L', 'R', 'G', 'B', 'Ha', 'OIII', etc.
    binning TEXT,                          -- '1x1', '2x2', etc.
    gain INTEGER,
    offset INTEGER,
    
    -- Timing
    datetime_start DATETIME,               -- Exposure start (UTC)
    datetime_end DATETIME,                 -- Exposure end (UTC)
    julian_date REAL,                      -- JD at mid-exposure
    
    -- Guiding and tracking
    guiding_enabled BOOLEAN,
    guiding_rms_arcsec REAL,
    guiding_rms_ra_arcsec REAL,
    guiding_rms_dec_arcsec REAL,
    
    -- Image quality
    fwhm_arcsec REAL,
    hfr REAL,
    eccentricity REAL,
    stars_detected INTEGER,
    background_adu REAL,
    
    -- Environmental conditions
    temperature_c REAL,                    -- Camera/ambient temperature
    humidity_percent REAL,
    pressure_mbar REAL,
    
    -- Telescope state
    telescope_ra REAL,                     -- Actual telescope RA (degrees)
    telescope_dec REAL,                    -- Actual telescope Dec (degrees)
    telescope_alt REAL,                    -- Altitude (degrees)
    telescope_az REAL,                     -- Azimuth (degrees)
    airmass REAL,
    
    -- Processing status
    calibrated BOOLEAN DEFAULT FALSE,      -- Has been calibrated (dark/flat/bias)
    plate_solved BOOLEAN DEFAULT FALSE,    -- Has been plate solved
    processed BOOLEAN DEFAULT FALSE,       -- Has been fully processed
    included_in_analysis BOOLEAN DEFAULT TRUE,  -- Include in photometry/analysis
    
    -- Quality flags
    quality_flag TEXT,                     -- 'good', 'acceptable', 'poor', 'rejected'
    rejection_reason TEXT,                 -- Why image was rejected
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    
    FOREIGN KEY (scheduled_target_id) REFERENCES scheduled_targets(scheduled_target_id) ON DELETE CASCADE
);

-- ============================================================================
-- OBSERVATION METADATA: Additional flexible metadata for observations
-- Key-value store for FITS headers and other properties
-- ============================================================================
CREATE TABLE IF NOT EXISTS observation_metadata (
    metadata_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    data_type TEXT,                        -- 'string', 'integer', 'float', 'boolean', 'datetime'
    
    FOREIGN KEY (observation_id) REFERENCES observations(observation_id) ON DELETE CASCADE,
    UNIQUE(observation_id, key)
);

-- ============================================================================
-- CALIBRATION FRAMES: Master calibration files used
-- ============================================================================
CREATE TABLE IF NOT EXISTS calibration_frames (
    calibration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_type TEXT NOT NULL,             -- 'bias', 'dark', 'flat'
    file_path TEXT NOT NULL UNIQUE,
    
    -- Calibration properties
    exposure_time_sec REAL,
    temperature_c REAL,
    binning TEXT,
    filter_name TEXT,
    gain INTEGER,
    offset INTEGER,
    
    -- Frame composition
    num_frames_stacked INTEGER,           -- How many frames in this master
    
    date_created DATE,
    valid_from DATE,
    valid_until DATE,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- ============================================================================
-- OBSERVATION_CALIBRATIONS: Link observations to calibration frames used
-- ============================================================================
CREATE TABLE IF NOT EXISTS observation_calibrations (
    obs_cal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL,
    calibration_id INTEGER NOT NULL,
    
    FOREIGN KEY (observation_id) REFERENCES observations(observation_id) ON DELETE CASCADE,
    FOREIGN KEY (calibration_id) REFERENCES calibration_frames(calibration_id) ON DELETE CASCADE,
    UNIQUE(observation_id, calibration_id)
);

-- ============================================================================
-- PHOTOMETRY RESULTS: Photometric measurements from observations
-- ============================================================================
CREATE TABLE IF NOT EXISTS photometry (
    photometry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_id INTEGER NOT NULL,
    
    -- Measurement details
    aperture_radius_pixels REAL,
    annulus_inner_radius_pixels REAL,
    annulus_outer_radius_pixels REAL,
    
    -- Raw measurements
    source_adu REAL,
    background_adu REAL,
    net_adu REAL,
    
    -- Calibrated measurements
    instrumental_magnitude REAL,
    magnitude_error REAL,
    calibrated_magnitude REAL,           -- After comparison star calibration
    
    -- SNR
    snr REAL,
    
    -- Comparison star info
    comp_star_1_mag REAL,
    comp_star_2_mag REAL,
    
    pipeline_version TEXT,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (observation_id) REFERENCES observations(observation_id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_obs_nights_date ON observation_nights(date_obs);
CREATE INDEX IF NOT EXISTS idx_scheduled_targets_night ON scheduled_targets(night_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_targets_target ON scheduled_targets(target_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_targets_status ON scheduled_targets(status);
CREATE INDEX IF NOT EXISTS idx_observations_scheduled ON observations(scheduled_target_id);
CREATE INDEX IF NOT EXISTS idx_observations_datetime ON observations(datetime_start);
CREATE INDEX IF NOT EXISTS idx_observations_quality ON observations(quality_flag);
CREATE INDEX IF NOT EXISTS idx_observations_filter ON observations(filter_name);
CREATE INDEX IF NOT EXISTS idx_metadata_obs ON observation_metadata(observation_id);
CREATE INDEX IF NOT EXISTS idx_photometry_obs ON photometry(observation_id);

-- ============================================================================
-- STAR COORDS CACHE: Persistent RA/Dec coordinate cache for variable stars
-- Avoids repeated SIMBAD/var.astro.cz lookups for the same targets each night
-- ============================================================================
CREATE TABLE IF NOT EXISTS star_coords_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    star_name TEXT NOT NULL UNIQUE,       -- Full combined name used in predictions (e.g., "EH Cnc", "G5341.00974")
    constellation TEXT,                    -- Constellation abbreviation (e.g., "Cnc")
    star_id TEXT,                          -- var.astro.cz numeric ID (primarily for G-stars)
    ra TEXT NOT NULL,                      -- RA in HH:MM:SS.SS format
    dec TEXT NOT NULL,                     -- Dec in ±DD:MM:SS.S format
    source TEXT,                           -- 'simbad' or 'varastro'
    lookup_date DATE DEFAULT (date('now')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_star_coords_name ON star_coords_cache(star_name);
CREATE INDEX IF NOT EXISTS idx_star_coords_star_id ON star_coords_cache(star_id);

-- ============================================================================
-- VIEWS for common queries
-- ============================================================================

-- View: Complete target information for a night
CREATE VIEW IF NOT EXISTS v_night_targets AS
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

-- View: Observation summary with target info
CREATE VIEW IF NOT EXISTS v_observations_summary AS
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

-- View: Nightly statistics
CREATE VIEW IF NOT EXISTS v_nightly_statistics AS
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

-- View: Target observation history
CREATE VIEW IF NOT EXISTS v_target_history AS
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
GROUP BY t.target_id, t.target_name, t.constellation, t.variability_type
ORDER BY nights_observed DESC, total_observations DESC;
