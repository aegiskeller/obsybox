# using a call to https://var.astro.cz/en/Stars/MinimaPredictions?pageId=1&pageSize=20&obsLat=50&obsLong=15&tabId=predTab1&date=2025-10-25&showVisibleEventsOnly=true
# with the users latitude and longitude set to -35 and 150 respectively
# we collect the minima predictions for the next night 
# from this list we draw targets for nina scheduling
import logging
import re
import sys
import time
import math
import json
import csv
import copy
import sqlite3
import traceback
import requests
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from secrets import VARASTRO_USERNAME, VARASTRO_PASSWORD
import tkinter as tk
from tkinter import messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Astropy imports for accurate astronomical calculations
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, SkyCoord as coord
from astropy.time import Time
import astropy.units as u
from astroquery.simbad import Simbad

# Import exposure time calculator
from exposure_time import get_exposure_time

# Import scheduling database function
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "logexploit" / "src"))
try:
    from logexploit.database import mark_targets_scheduled
except ImportError:
    mark_targets_scheduled = None  # Optional dependency

# Import local observation database
from observation_db import ObservationDB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration from persistent storage
try:
    from config import get_flat_config
    config = get_flat_config()
    LATITUDE = config['LATITUDE']
    LONGITUDE = config['LONGITUDE']
    MAG_MIN = config['MAG_MIN']
    MAG_MAX = config['MAG_MAX']
    MIN_ALTITUDE = config['MIN_ALTITUDE']
    MIN_ALTITUDE_DURING_OBS = config['MIN_ALTITUDE_DURING_OBS']
    MIN_DECLINATION = config['MIN_DECLINATION']
    MAX_DECLINATION = config['MAX_DECLINATION']
    OBSERVATION_WINDOW = config['OBSERVATION_WINDOW']
    TARGET_SPACING = config['TARGET_SPACING']
    CENTER_AFTER_DRIFT_ARCMIN = config['CENTER_AFTER_DRIFT_ARCMIN']
    MAX_TARGETS_PER_NIGHT = config['MAX_TARGETS_PER_NIGHT']
    TIMEZONE_OFFSET = config['TIMEZONE_OFFSET']
    ALLOWED_AZIMUTHS = config['ALLOWED_AZIMUTHS']
    ALLOW_G_TARGETS = config['ALLOW_G_TARGETS']
    NINA_EXPORT_BASE_DIR = config['NINA_EXPORT_BASE_DIR']
except ImportError:
    logger.warning("Config module not found, using hardcoded defaults")
    # Fallback to hardcoded values
    LATITUDE = -35
    LONGITUDE = 149.08
    MAG_MIN = 10
    MAG_MAX = 12.5
    MIN_ALTITUDE = 45
    MIN_ALTITUDE_DURING_OBS = 30
    MIN_DECLINATION = -40
    MAX_DECLINATION = 0
    OBSERVATION_WINDOW = 4
    TARGET_SPACING = 4
    CENTER_AFTER_DRIFT_ARCMIN = 1.5
    MAX_TARGETS_PER_NIGHT = 2
    TIMEZONE_OFFSET = 10
    ALLOWED_AZIMUTHS = ['N', 'NE', 'NW', 'E', 'W']
    ALLOW_G_TARGETS = True
    NINA_EXPORT_BASE_DIR = r"C:\Users\aegis\Documents\N.I.N.A\Targets\VarStars"

# Web scraping configuration
BASE_URL = "https://var.astro.cz/en/Stars/MinimaPredictions"
USERNAME = VARASTRO_USERNAME
PASSWORD = VARASTRO_PASSWORD

# NINA template configuration
NINA_TEMPLATE_FILE = "VarStarS50.template.json"  # Template file for NINA JSON generation (relative to script directory)
# check if the template file exists
template_path = Path(__file__).parent / NINA_TEMPLATE_FILE
if not template_path.exists():
    logger.error(f"NINA template file not found: {template_path}") 
    # Handle the error (e.g., exit or use a default template)
    # For development, we'll continue without exiting
    logger.warning("Continuing without template - functions may fail") 

# Fixed parameters (not user-configurable)
SUNSET_TIME = "20:00"  # Default sunset time LOCAL TIME
STAR_COORDS_DB_PATH = Path("Z:/scheduled_observations.sqlite")  # Persistent star coordinate cache

def fetch_minima_predictions(obs_date: date = None, max_pages: int = None, use_cache: bool = True) -> List[Dict]:
    """
    Fetch minima predictions from var.astro.cz using Selenium
    
    Args:
        obs_date: Observation date (defaults to today for tonight's observations)
        max_pages: Maximum number of pages to fetch (None = all pages, useful for testing)
        use_cache: If True, use cached data if available for the same date
        
    Returns:
        List of target dictionaries
    """
    if obs_date is None:
        obs_date = date.today()
    
    # Use the observation date directly - this is what goes in the website's date box
    # For observation night 2025-11-02, we want to request 2025-11-02 from the website
    logger.info(f"Using observation date {obs_date} for predictions request")
    
    # Check for cached data
    cache_file = Path(__file__).parent / f"cache_raw_targets_{obs_date}.json"
    if use_cache and cache_file.exists():
        logger.info(f"Found cached data for {obs_date}, loading from {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            targets = json.load(f)
        logger.info(f"Loaded {len(targets)} targets from cache")
        
        # Apply basic filters to cached data
        filtered_targets = apply_filters(targets)
        logger.info(f"After applying basic filters: {len(filtered_targets)} targets remain")
        
        # Apply observation night filtering with correct timezone handling
        night_filtered_targets = filter_targets_by_observation_night(filtered_targets, obs_date)
        logger.info(f"After observation night filtering: {len(night_filtered_targets)} targets remain")
        
        return night_filtered_targets
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome driver initialized")
        
        # Navigate to login page
        login_url = "https://var.astro.cz/en/Identity/Account/Login"
        driver.get(login_url)
        logger.info("Loading login page...")
        
        # Fill in login form
        email_field = driver.find_element(By.ID, "user-name")
        password_field = driver.find_element(By.ID, "user-password")
        
        email_field.send_keys(USERNAME)
        password_field.send_keys(PASSWORD)
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        logger.info("Login submitted, waiting for redirect...")
        
        # Wait for login to complete
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "header-navbar"))
        )
        logger.info("Login successful")
        
        # Navigate to predictions page with initial parameters
        # Use YYYY-MM-DD format to match what the website's date field expects
        pred_url = (f"https://var.astro.cz/en/Stars/MinimaPredictions?init=1"
                   f"&obsLat={LATITUDE}&obsLong={LONGITUDE}"
                   f"&date={obs_date.strftime('%Y-%m-%d')}"

                   f"&showVisibleEventsOnly=true")
        logger.info(f"Requesting predictions for date: {obs_date.strftime('%Y-%m-%d')} (YYYY-MM-DD format)")
        logger.info(f"URL: {pred_url}")
        driver.get(pred_url)
        logger.info(f"Loading predictions page for {obs_date}...")
        
        # Wait for page to load but NOT for the table yet - we need to set the date first
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # CRITICAL: Set the date field IMMEDIATELY after page load and BEFORE applying other filters
        try:
            # The correct date field is 'pred-date' - use JavaScript to set it directly
            date_set = False
            # Use DD/MM/YYYY format as expected by the website (e.g., "02/11/2025" for Nov 2, 2025)
            target_date = obs_date.strftime('%d/%m/%Y')
            
            try:
                # First, check current value and field attributes
                inspection_script = """
                var dateField = document.getElementById('pred-date');
                if (dateField) {
                    return {
                        value: dateField.value,
                        type: dateField.type,
                        pattern: dateField.pattern || 'none',
                        placeholder: dateField.placeholder || 'none',
                        className: dateField.className,
                        required: dateField.required
                    };
                } else {
                    return 'NOT_FOUND';
                }
                """
                field_info = driver.execute_script(inspection_script)
                logger.info(f"Date field info: {field_info}")
                
                # Based on current value '2025-11-01', the field expects YYYY-MM-DD format!
                formats_to_try = [
                    obs_date.strftime('%Y-%m-%d'),  # YYYY-MM-DD (2025-11-02) - matches field format
                    obs_date.strftime('%d/%m/%Y'),  # DD/MM/YYYY (02/11/2025) - fallback
                    obs_date.strftime('%m/%d/%Y'),  # MM/DD/YYYY (11/02/2025) - fallback
                ]
                
                logger.info(f"Will try date formats: {formats_to_try}")
                
                for i, date_format in enumerate(formats_to_try):
                    script = f"""
                    var dateField = document.getElementById('pred-date');
                    if (dateField) {{
                        dateField.value = '{date_format}';
                        dateField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        dateField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        return dateField.value;
                    }} else {{
                        return 'NOT_FOUND';
                    }}
                    """
                    
                    new_value = driver.execute_script(script)
                    logger.info(f"Attempt {i+1}: Set date to '{date_format}', field now shows: '{new_value}'")
                    
                    if new_value == date_format:
                        date_set = True
                        target_date = date_format  # Update for logging
                        logger.info(f"✅ Date field successfully set with format {i+1}: {date_format}")
                        break
                    elif new_value == 'NOT_FOUND':
                        logger.error("❌ Date field 'pred-date' not found!")
                        break
                if not date_set:
                    logger.warning(f"⚠️  All date format attempts failed. Field value remains: '{new_value}'")
                
                # Also trigger form submission or page reload to ensure changes take effect
                if date_set:
                    logger.info("Triggering form update...")
                    driver.execute_script("""

                        // Look for and click a submit or update button
                        var submitButton = document.querySelector('button[type="submit"]') || 
                                         document.querySelector('input[type="submit"]') ||
                                         document.querySelector('button:contains("Update")') ||
                                         document.querySelector('button:contains("Search")');
                        if (submitButton) {
                            submitButton.click();
                        } else {
                            // Trigger a form event to update the table
                            var form = document.querySelector('form');
                            if (form) {
                                form.dispatchEvent(new Event('submit', { bubbles: true }));
                            }
                        }
                    """)
                    
            except Exception as e:
                logger.error(f"Failed to set date field using JavaScript: {e}")
            
            if not date_set:
                logger.error(f"❌ FAILED to set date field! This will result in wrong targets (yesterday's data)!")

                logger.error(f"Expected date: {target_date}")
            
            # Wait longer for table to reload after date change
            import time
            time.sleep(8)  # Increased wait time for form submission/page reload
            
        except Exception as e:
            logger.error(f"Error setting date field: {e}")
        
        # Now wait for the table to be present (should have correct date now)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "minima-pred-table"))
        )
        
        # Fill in other filter fields (date is already set above)
        try:
            # Magnitude max filter
            mag_max_input = driver.find_element(By.ID, "fMagMax")
            mag_max_input.clear()
            mag_max_input.send_keys(f"<{MAG_MAX}")
            
            # Magnitude min filter  
            mag_min_input = driver.find_element(By.ID, "fMagMin")
            mag_min_input.clear()
            mag_min_input.send_keys(f">{MAG_MIN}")
            
            # Altitude filter
            altitude_input = driver.find_element(By.ID, "fAltitude")
            altitude_input.clear()
            altitude_input.send_keys(f">{MIN_ALTITUDE}")
            
            # Azimuth filter - try entering as comma-separated
            azimuth_input = driver.find_element(By.ID, "fAzimuth")
            azimuth_input.clear()
            azimuth_filter = ','.join(ALLOWED_AZIMUTHS)
            azimuth_input.send_keys(azimuth_filter)
            
            logger.info(f"Applied filters: date={obs_date.strftime('%Y-%m-%d')}, mag {MAG_MIN}-{MAG_MAX}, alt >{MIN_ALTITUDE}°, azimuth={azimuth_filter}")
            
            # Press Enter to apply filters
            from selenium.webdriver.common.keys import Keys
            azimuth_input.send_keys(Keys.RETURN)
            
            # Wait for table to reload
            time.sleep(5)
            
        except Exception as e:
            logger.warning(f"Could not apply filters via form fields: {e}")
        
        logger.info("Table element found, waiting for data...")
        
        # Wait for DataTable to finish loading - check for processing indicator to disappear
        import time
        time.sleep(5)  # Give DataTable time to make AJAX request
        
        # Wait for table rows to populate (not the "No data" message)
        WebDriverWait(driver, 30).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#minima-pred-table tbody tr")) > 0
        )
        
        # Additional wait to ensure all data is loaded
        time.sleep(2)
        logger.info("Table loaded, extracting data...")
        
        # Check if we need to change page size in DataTable
        try:
            # Look for the "Show X entries" dropdown
            length_menu = driver.find_element(By.CSS_SELECTOR, "select[name='minima-pred-table_length']")
            # Select "All" or a larger number
            from selenium.webdriver.support.ui import Select
            select = Select(length_menu)
            
            # Try to select the largest option (usually 100 or "All")
            options = [opt.get_attribute('value') for opt in select.options]
            logger.info(f"Available page size options: {options}")
            
            # Select the largest numeric option or -1 for "All"
            if '-1' in options:
                select.select_by_value('-1')
                logger.info("Selected 'All' entries")
            else:
                # Select the largest number
                numeric_options = [int(opt) for opt in options if opt.isdigit()]
                if numeric_options:
                    max_option = max(numeric_options)
                    select.select_by_value(str(max_option))
                    logger.info(f"Selected {max_option} entries per page")
            
            # Wait for table to reload with new page size
            time.sleep(3)
        except Exception as e:
            logger.warning(f"Could not change page size: {e}")
        
        # Get total number of entries from DataTable info
        total_entries = 0
        try:
            info_text = driver.find_element(By.ID, "minima-pred-table_info").text
            # Extract number from text like "Showing 1 to 100 of 250 entries"
            import re
            match = re.search(r'of\s+(\d+)\s+entries', info_text)
            if match:
                total_entries = int(match.group(1))
                logger.info(f"Total entries available: {total_entries}")
        except Exception as e:
            logger.warning(f"Could not get total entries count: {e}")
        
        # Extract all targets by iterating through pages
        targets = []
        page_num = 1
        
        while True:
            # Extract data from current page
            table = driver.find_element(By.ID, "minima-pred-table")
            rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            logger.info(f"Page {page_num}: Found {len(rows)} rows")
            
            page_targets = 0
            for i, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                
                # Check if this is a "no data" row
                if len(cells) == 1 and 'no data' in cells[0].text.lower():
                    logger.warning("Table shows 'No data available'")
                    break
                    
                if len(cells) >= 10:
                    # Extract basic visible data
                    star_name = cells[2].text.strip()
                    constellation = cells[3].text.strip()
                    
                    # For named variables (not WDS catalog), combine name with constellation
                    # WDS targets start with 'G' followed by numbers
                    if star_name and not star_name.startswith('G'):
                        # Named variable: combine name and constellation (e.g., "CH" + "Scl" = "CH Scl")
                        # But check first if the constellation is already part of the name
                        # (some entries show "EH Cnc" in the name column with "Cnc" in constellation)
                        if constellation and not star_name.strip().lower().endswith(constellation.strip().lower()):
                            full_name = f"{star_name} {constellation}"
                        else:
                            full_name = star_name
                    else:
                        # WDS catalog target: keep as-is (e.g., "G1234.56789")
                        full_name = star_name
                    
                    target = {
                        'id': cells[0].text.strip(),
                        'entries': cells[1].text.strip(),
                        'name': full_name,
                        'constellation': constellation,
                        'minima_type': cells[4].text.strip(),
                        'mag_max': cells[5].text.strip(),
                        'mag_min': cells[6].text.strip(),
                        'band': cells[7].text.strip() if len(cells) > 7 else '',
                        'variability_type': cells[8].text.strip() if len(cells) > 8 else '',
                        'minimum_time': cells[9].text.strip() if len(cells) > 9 else '',
                        'altitude': cells[10].text.strip() if len(cells) > 10 else '',
                        'azimuth': cells[11].text.strip() if len(cells) > 11 else '',
                    }
                    
                    # Try to get RA/Dec from DataTables API using JavaScript
                    # The DataTable may have the data even if columns aren't visible
                    try:
                        # Execute JavaScript to get row data from DataTable API
                        row_data = driver.execute_script("""


                            var table = $('#minima-pred-table').DataTable();
                            var rowData = table.row(arguments[0]).data();
                            return rowData;
                        """, i)
                        
                        if row_data and len(row_data) > 18:
                            # RA is typically at index 18, Dec at 19 based on table structure
                            target['ra'] = str(row_data[18]).strip() if row_data[18] else ''
                            target['dec'] = str(row_data[19]).strip() if row_data[19] else ''
                        else:
                            target['ra'] = ''
                            target['dec'] = ''
                    except Exception as e:
                        logger.debug(f"Could not extract RA/Dec from DataTable API: {e}")
                        target['ra'] = ''
                        target['dec'] = ''
                    
                    targets.append(target)
                    page_targets += 1
            
            logger.info(f"Extracted {page_targets} targets from page {page_num}")
            
            # Check if there's a next page button and if it's enabled
            try:
                next_button = driver.find_element(By.ID, "minima-pred-table_next")
                if 'disabled' in next_button.get_attribute('class'):
                    logger.info("No more pages available")
                    break
                
                # Click next page
                next_button.click()
                logger.info(f"Moving to page {page_num + 1}...")
                time.sleep(3)  # Wait for page to load
                page_num += 1
                
                # Check if we've reached the max pages limit (for testing)
                if max_pages and page_num > max_pages:
                    logger.info(f"Reached maximum page limit ({max_pages}), stopping")
                    break
                
                # Safety check to prevent infinite loops
                if page_num > 50:
                    logger.warning("Reached maximum page limit (50), stopping")
                    break
                    
            except Exception as e:
                logger.info(f"No next page found or error clicking: {e}")
                break
        
        logger.info(f"Found {len(targets)} total targets across {page_num} page(s)")
        
        # Apply quick filters BEFORE coordinate enrichment to reduce workload
        logger.info("Applying basic filters (magnitude, altitude, azimuth, G-targets)...")
        filtered_targets = apply_basic_filters(targets)
        logger.info(f"After basic filters: {len(filtered_targets)} targets remain (saved {len(targets) - len(filtered_targets)} coordinate lookups)")
        
        # Apply observation night filtering
        night_filtered_targets = filter_targets_by_observation_night(filtered_targets, obs_date)
        logger.info(f"After observation night filtering: {len(night_filtered_targets)} targets remain")
        
        # NOW enrich only the filtered targets with coordinates
        logger.info(f"Resolving coordinates for {len(night_filtered_targets)} filtered targets...")
        night_filtered_targets = enrich_targets_with_coordinates(night_filtered_targets, driver)
        logger.info("Coordinate resolution complete")
        
        # Save enriched and filtered data to cache
        cache_file = Path(__file__).parent / f"cache_raw_targets_{obs_date}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(night_filtered_targets, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved enriched data to cache: {cache_file}")
        
        # Final filter check for any remaining issues
        final_targets = apply_final_filters(night_filtered_targets)
        logger.info(f"After final filters: {len(final_targets)} targets remain")
        
        return final_targets
        
    except Exception as e:
        logger.error(f"Error fetching data with Selenium: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Save page source for debugging
        if driver:
            try:
                debug_path = Path(__file__).parent / "selenium_debug.html"
                debug_path.write_text(driver.page_source)
                logger.info(f"Page source saved to {debug_path}")
            except:
                pass
        return []
    finally:
        if driver:
            driver.quit()

# ---------------------------------------------------------------------------
# Persistent star coordinate cache (avoids re-resolving the same stars nightly)
# ---------------------------------------------------------------------------

_COORDS_CACHE_DDL = """
    CREATE TABLE IF NOT EXISTS star_coords_cache (
        cache_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        star_name   TEXT NOT NULL UNIQUE,
        constellation TEXT,
        star_id     TEXT,
        ra          TEXT NOT NULL,
        dec         TEXT NOT NULL,
        source      TEXT,
        lookup_date DATE DEFAULT (date('now')),
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_star_coords_name ON star_coords_cache(star_name);
    CREATE INDEX IF NOT EXISTS idx_star_coords_star_id ON star_coords_cache(star_id);
"""

def _cache_get_coords(star_name: str):
    """Return (ra, dec) from the persistent DB cache, or (None, None) on miss/error."""
    if not STAR_COORDS_DB_PATH.exists():
        return (None, None)
    try:
        conn = sqlite3.connect(str(STAR_COORDS_DB_PATH))
        conn.executescript(_COORDS_CACHE_DDL)  # no-op if table already exists
        cur = conn.execute(
            "SELECT ra, dec FROM star_coords_cache WHERE star_name = ?",
            (star_name,)
        )
        row = cur.fetchone()
        conn.close()
        if row:
            logger.debug(f"Coord cache HIT for '{star_name}': RA={row[0]}, Dec={row[1]}")
            return (row[0], row[1])
    except Exception as e:
        logger.debug(f"Coord cache read error for '{star_name}': {e}")
    return (None, None)


def _cache_set_coords(star_name: str, ra: str, dec: str,
                      constellation: str = '', star_id: str = '', source: str = ''):
    """Write (ra, dec) to the persistent DB cache; silently ignores errors."""
    if not STAR_COORDS_DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(str(STAR_COORDS_DB_PATH))
        conn.executescript(_COORDS_CACHE_DDL)  # no-op if table already exists
        conn.execute("""
            INSERT INTO star_coords_cache
                (star_name, constellation, star_id, ra, dec, source, lookup_date)
            VALUES (?, ?, ?, ?, ?, ?, date('now'))
            ON CONFLICT(star_name) DO UPDATE SET
                ra          = excluded.ra,
                dec         = excluded.dec,
                source      = excluded.source,
                lookup_date = date('now')
        """, (star_name, constellation, star_id, ra, dec, source))
        conn.commit()
        conn.close()
        logger.debug(f"Coord cache written for '{star_name}' (source={source})")
    except Exception as e:
        logger.debug(f"Coord cache write error for '{star_name}': {e}")


# ---------------------------------------------------------------------------

def enrich_targets_with_coordinates(targets: List[Dict], driver=None, max_workers: int = 5) -> List[Dict]:
    """
    Enrich targets with RA/Dec coordinates by looking them up from SIMBAD or var.astro.cz
    
    Uses parallel threading to speed up coordinate lookups.
    
    Args:
        targets: List of target dictionaries
        driver: Existing Selenium webdriver (optional, will create new ones per thread)
        max_workers: Maximum number of parallel threads (default: 5)
        
    Returns:
        Enriched list of targets with coordinates filled in
    """
    stats = {
        'total': len(targets),
        'already_had_coords': 0,
        'db_cache_hit': 0,
        'simbad_success': 0,
        'varastro_success': 0,
        'lookup_failed': 0
    }
    stats_lock = Lock()
    progress_lock = Lock()
    completed_count = [0]  # Use list to allow modification in nested function
    
    def lookup_single_target(index_and_target):
        """Lookup coordinates for a single target (thread-safe).

        Resolution order:
          1. Already present in the target dict (from the per-night cache/scrape)
          2. Persistent DB coordinate cache  (star_coords_cache table)
          3. SIMBAD (named variables)
          4. var.astro.cz star page (G-catalog & fallback)
        """
        i, target = index_and_target
        ra = target.get('ra', '').strip()
        dec = target.get('dec', '').strip()

        # 1. Skip if the target dict already carries coordinates
        if ra and dec:
            with stats_lock:
                stats['already_had_coords'] += 1
            return target

        star_name = target.get('name', '')
        constellation = target.get('constellation', '')
        star_id = target.get('id', '')

        # 2. Check the persistent DB coordinate cache first (fast, no network)
        ra_cached, dec_cached = _cache_get_coords(star_name)
        if ra_cached and dec_cached:
            target['ra'] = ra_cached
            target['dec'] = dec_cached
            with stats_lock:
                stats['db_cache_hit'] += 1
            return target

        # 3a. G catalog stars - resolve via var.astro.cz
        if star_name.startswith('G') and star_id:
            ra_new, dec_new = fetch_coordinates_from_varastro(star_id, driver=None)
            if ra_new and dec_new:
                target['ra'] = ra_new
                target['dec'] = dec_new
                _cache_set_coords(star_name, ra_new, dec_new,
                                  constellation=constellation, star_id=star_id,
                                  source='varastro')
                with stats_lock:
                    stats['varastro_success'] += 1
            else:
                with stats_lock:
                    stats['lookup_failed'] += 1
            return target

        # 3b. Try SIMBAD first for non-G catalog stars
        ra_new, dec_new = lookup_coordinates_simbad(star_name, constellation)
        if ra_new and dec_new:
            target['ra'] = ra_new
            target['dec'] = dec_new
            _cache_set_coords(star_name, ra_new, dec_new,
                              constellation=constellation, star_id=star_id,
                              source='simbad')
            with stats_lock:
                stats['simbad_success'] += 1
            return target

        # 4. SIMBAD failed - fall back to var.astro.cz
        if star_id:
            ra_new, dec_new = fetch_coordinates_from_varastro(star_id, driver=None)
            if ra_new and dec_new:
                target['ra'] = ra_new
                target['dec'] = dec_new
                _cache_set_coords(star_name, ra_new, dec_new,
                                  constellation=constellation, star_id=star_id,
                                  source='varastro')
                with stats_lock:
                    stats['varastro_success'] += 1
                return target

        # Could not resolve coordinates by any method
        with stats_lock:
            stats['lookup_failed'] += 1
        return target
    
    def update_progress():
        """Thread-safe progress update"""
        with progress_lock:
            completed_count[0] += 1
            if completed_count[0] % 10 == 0 or completed_count[0] == stats['total']:
                percent_complete = (completed_count[0] / stats['total']) * 100
                logger.info(f"Progress: {completed_count[0]}/{stats['total']} targets processed ({percent_complete:.1f}%)")
    
    # Separate targets that need lookup from those that don't
    targets_needing_lookup = []
    targets_with_coords = []
    
    for i, target in enumerate(targets):
        ra = target.get('ra', '').strip()
        dec = target.get('dec', '').strip()
        if ra and dec:
            targets_with_coords.append(target)
            stats['already_had_coords'] += 1
        else:
            targets_needing_lookup.append((i, target))
    
    logger.info(f"Coordinate enrichment: {len(targets_with_coords)} targets already have coords, "
                f"{len(targets_needing_lookup)} need lookup")
    
    if not targets_needing_lookup:
        return targets
    
    logger.info(f"Using {max_workers} parallel threads for coordinate lookups...")
    
    # Process lookups in parallel
    enriched_targets = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all lookup tasks
        future_to_target = {
            executor.submit(lookup_single_target, item): item 
            for item in targets_needing_lookup
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_target):
            try:
                result = future.result()
                enriched_targets.append(result)
                update_progress()
            except Exception as e:
                index, target = future_to_target[future]
                logger.error(f"Error processing target '{target.get('name', 'unknown')}': {e}")
                enriched_targets.append(target)
                update_progress()
    
    # Combine results (maintaining original order)
    all_targets = targets_with_coords + enriched_targets
    
    logger.info(f"Coordinate enrichment complete: "
                f"{stats['already_had_coords']} already had coords, "
                f"{stats['db_cache_hit']} from DB cache, "
                f"{stats['simbad_success']} from SIMBAD, "
                f"{stats['varastro_success']} from var.astro.cz, "
                f"{stats['lookup_failed']} failed")
    
    return all_targets


def apply_basic_filters(targets: List[Dict]) -> List[Dict]:
    """
    Apply basic filters that don't require coordinates
    (magnitude, altitude at minima, azimuth, G-targets)
    
    Args:
        targets: List of target dictionaries
        
    Returns:
        Filtered list of targets
    """
    filtered = []
    stats = {
        'magnitude_filtered': 0,
        'altitude_filtered': 0,
        'azimuth_filtered': 0,
        'g_targets_filtered': 0,
        'passed': 0
    }
    
    for target in targets:
        passed = True
        
        # Filter by G-targets if not allowed
        if not ALLOW_G_TARGETS:
            target_name = target.get('name', '')
            if target_name.startswith('G') and '.' in target_name:
                # Check if it matches the pattern Gnnnn.nnnnn (G followed by digits, dot, digits)
                import re
                if re.match(r'^G\d+\.\d+', target_name):
                    stats['g_targets_filtered'] += 1
                    passed = False
                    continue
        
        # Filter by magnitude
        # Star's max mag should be > GUI's min mag AND star's min mag should be < GUI's max mag
        try:
            mag_max = float(target.get('mag_max', '0').replace(',', '.'))
            mag_min = float(target.get('mag_min', '0').replace(',', '.'))
            
            # Handle invalid magnitude ranges where min is 0 (treat both as mag_max)
            if mag_min == 0 and mag_max > 0:
                mag_min = mag_max
            
            # Target is valid if: star's max magnitude > GUI min AND star's min magnitude < GUI max
            if not (mag_max > MAG_MIN and mag_min < MAG_MAX):
                stats['magnitude_filtered'] += 1
                passed = False
                continue
        except (ValueError, AttributeError):
            passed = False
            continue
        
        # Filter by altitude at minima (doesn't need RA/Dec)
        try:
            altitude = float(target.get('altitude', '0'))
            if altitude < MIN_ALTITUDE:
                stats['altitude_filtered'] += 1
                passed = False
                continue
        except (ValueError, AttributeError):
            passed = False
            continue
        
        # Filter by azimuth
        azimuth = target.get('azimuth', '').strip().upper()
        if azimuth and not any(allowed in azimuth for allowed in ALLOWED_AZIMUTHS):
            stats['azimuth_filtered'] += 1
            passed = False
            continue
        
        if passed:
            filtered.append(target)
            stats['passed'] += 1
    
    logger.info(f"Basic filter stats: {stats['passed']} passed, "
                f"{stats['magnitude_filtered']} filtered by magnitude, "
                f"{stats['altitude_filtered']} filtered by altitude, "
                f"{stats['azimuth_filtered']} filtered by azimuth, "
                f"{stats['g_targets_filtered']} G-targets filtered")
    
    return filtered


def apply_final_filters(targets: List[Dict]) -> List[Dict]:
    """
    Apply final filters that require coordinates (after enrichment)
    
    Args:
        targets: List of target dictionaries with coordinates
        
    Returns:
        Filtered list of targets
    """
    filtered = []
    stats = {
        'coordinates_filtered': 0,
        'passed': 0
    }
    
    for target in targets:
        passed = True
        
        # Check for valid RA/Dec coordinates (should already be in cache)
        ra = target.get('ra', '').strip()
        dec = target.get('dec', '').strip()
        
        # Filter out targets that still don't have coordinates
        if not ra or not dec:
            star_name = target.get('name', '')
            logger.warning(f"Target '{star_name}' missing coordinates (coordinate lookup failed), filtering out")
            stats['coordinates_filtered'] += 1
            passed = False
            continue
        
        if passed:
            filtered.append(target)
            stats['passed'] += 1
    
    logger.info(f"Final filter stats: {stats['passed']} passed, "
                f"{stats['coordinates_filtered']} filtered (missing coordinates)")
    
    return filtered


def apply_filters(targets: List[Dict]) -> List[Dict]:
    """
    Apply ALL filters to the targets list (for cached data)
    This is used when loading from cache - runs both basic and final filters
    
    Args:
        targets: List of target dictionaries
        
    Returns:
        Filtered list of targets
    """
    # Apply basic filters first
    filtered = apply_basic_filters(targets)
    # Apply basic filters first
    filtered = apply_basic_filters(targets)
    # Then apply final filters
    filtered = apply_final_filters(filtered)
    return filtered


def filter_targets_by_observation_night(targets: List[Dict], observation_date: date) -> List[Dict]:
    """
    Filter targets to only include those with minima occurring during the observation night.
    Observation nights run from noon of observation_date to noon of the next day.
    
    Args:
        targets: List of target dictionaries with minima times
        observation_date: Date representing the observation night (noon-to-noon)
    
    Returns:
        Filtered list of targets with minima during the observation night
    """
    # Observation night runs from noon LOCAL TIME of observation_date to noon LOCAL TIME of next day
    # Convert to UTC for comparison with target minima times
    
    # Noon local time on observation_date
    noon_local = datetime.combine(observation_date, datetime.min.time()) + timedelta(hours=12)
    night_start_utc = local_to_utc(noon_local)
    
    # Noon local time on next day  
    next_day = observation_date + timedelta(days=1)
    noon_next_local = datetime.combine(next_day, datetime.min.time()) + timedelta(hours=12)
    night_end_utc = local_to_utc(noon_next_local)
    
    logger.info(f"Filtering targets for observation night: {observation_date}")
    logger.info(f"Night window (LOCAL): {noon_local.strftime('%Y-%m-%d %H:%M')} to {noon_next_local.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"Night window (UTC):   {night_start_utc.strftime('%Y-%m-%d %H:%M')} to {night_end_utc.strftime('%Y-%m-%d %H:%M')}")
    
    filtered_targets = []
    
    for target in targets:
        try:
            # Parse the minima time (expecting format: "MM/DD/YY, HH:MM" in UTC)
            minima_str = target.get('minimum_time', '')
            if not minima_str:
                continue
                
            minima_utc = parse_minima_time(minima_str)
            if not minima_utc:
                continue
            
            # Check if minima falls within the observation night window (all times in UTC)
            if night_start_utc <= minima_utc <= night_end_utc:
                filtered_targets.append(target)
                logger.debug(f"Target {target.get('name', 'Unknown')} minima at {minima_str} UTC - INCLUDED")
            else:
                logger.debug(f"Target {target.get('name', 'Unknown')} minima at {minima_str} UTC - EXCLUDED (outside night window)")
                
        except (ValueError, KeyError) as e:
            logger.debug(f"Warning: Could not parse minima time for target {target.get('name', 'Unknown')}: {e}")
            continue
    
    logger.info(f"Filtered to {len(filtered_targets)} targets with minima during observation night")
    return filtered_targets

def parse_minima_time(time_str: str) -> datetime:
    """
    Parse minima time string to datetime object (UTC)
    
    Args:
        time_str: Time string like "10/25/25, 09:22" (UTC)
        
    Returns:
        datetime object in UTC
    """
    try:
        # Handle format "10/25/25, 09:22"
        return datetime.strptime(time_str, "%m/%d/%y, %H:%M")
    except ValueError:
        try:
            # Alternative format
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.error(f"Could not parse time: {time_str}")
            return None

def utc_to_local(utc_time: datetime) -> datetime:
    """Convert UTC time to local time"""
    return utc_time + timedelta(hours=TIMEZONE_OFFSET)

def local_to_utc(local_time: datetime) -> datetime:
    """Convert local time to UTC"""
    return local_time - timedelta(hours=TIMEZONE_OFFSET)

def calculate_astronomical_dawn(obs_date: date, lat: float, lon: float) -> str:
    """
    Calculate astronomical dawn time (sun at -18° altitude) for the next day
    
    Args:
        obs_date: Observation date  
        lat: Observer latitude in degrees
        lon: Observer longitude in degrees
        
    Returns:
        Time as "HH:MM" string in LOCAL TIME when sun reaches -18° (astronomical dawn)
    """
    # Calculate for the next day (dawn after the observation night)
    next_day = obs_date + timedelta(days=1)
    
    # Use the same calculation as sunset but for dawn (sun rising from -18°)
    year = next_day.year
    month = next_day.month
    day = next_day.day
    
    if month <= 2:
        year -= 1
        month += 12
    
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    
    # Number of days since J2000.0
    n = jd - 2451545.0
    
    # Mean solar time
    J_star = n - lon / 360.0
    
    # Solar mean anomaly
    M = (357.5291 + 0.98560028 * J_star) % 360
    M_rad = math.radians(M)
    
    # Equation of center
    C = 1.9148 * math.sin(M_rad) + 0.0200 * math.sin(2 * M_rad) + 0.0003 * math.sin(3 * M_rad)
    
    # Ecliptic longitude
    lambda_sun = (M + C + 180 + 102.9372) % 360
    
    # Solar transit
    J_transit = 2451545.0 + J_star + 0.0053 * math.sin(M_rad) - 0.0069 * math.sin(2 * math.radians(lambda_sun))
    
    # Declination of the sun
    sin_dec = math.sin(math.radians(lambda_sun)) * math.sin(math.radians(23.44))
    cos_dec = math.sqrt(1 - sin_dec**2)
    
    # Hour angle for astronomical twilight (-18°)
    lat_rad = math.radians(lat)
    sun_alt_rad = math.radians(-18.0)
    
    cos_omega = (math.sin(sun_alt_rad) - math.sin(lat_rad) * sin_dec) / (math.cos(lat_rad) * cos_dec)
    
    # Check if sun reaches this altitude
    if cos_omega > 1:
        return "06:00"  # Default if sun doesn't reach -18° (polar regions)
    elif cos_omega < -1:
        return "06:00"  # Default if sun doesn't reach -18°
    
    omega = math.degrees(math.acos(cos_omega))
    
    # Time when sun reaches -18° altitude (rising/dawn)
    J_rise = J_transit - omega / 360.0
    
    # Convert to local time
    dawn_hour = ((J_rise - jd) * 24 + 12 + TIMEZONE_OFFSET) % 24
    
    hours = int(dawn_hour)
    minutes = int((dawn_hour - hours) * 60)
    
    return f"{hours:02d}:{minutes:02d}"

def calculate_sunset_time(obs_date: date, lat: float, lon: float, sun_altitude: float = -15.0) -> str:
    """
    Calculate the time when sun reaches a specific altitude below horizon
    Default is -15° for dark sky observations (between nautical and astronomical twilight)
    
    Uses simplified astronomical formulas
    
    Args:
        obs_date: Observation date
        lat: Observer latitude in degrees
        lon: Observer longitude in degrees
        sun_altitude: Sun altitude in degrees (negative = below horizon)
                     -0.833 = sunset (default atmospheric refraction)
                     -6 = civil twilight
                     -12 = nautical twilight
                     -15 = dark enough for astronomy (between nautical and astronomical)
                     -18 = astronomical twilight
        
    Returns:
        Time as "HH:MM" string in LOCAL TIME when sun reaches specified altitude
    """
    # Julian day calculation
    year = obs_date.year
    month = obs_date.month
    day = obs_date.day
    
    if month <= 2:
        year -= 1
        month += 12
    
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    
    # Number of days since J2000.0
    n = jd - 2451545.0
    
    # Mean solar time
    J_star = n - lon / 360.0
    
    # Solar mean anomaly
    M = (357.5291 + 0.98560028 * J_star) % 360
    M_rad = math.radians(M)
    
    # Equation of center
    C = 1.9148 * math.sin(M_rad) + 0.0200 * math.sin(2 * M_rad) + 0.0003 * math.sin(3 * M_rad)
    
    # Ecliptic longitude
    lambda_sun = (M + C + 180 + 102.9372) % 360
    
    # Solar transit
    J_transit = 2451545.0 + J_star + 0.0053 * math.sin(M_rad) - 0.0069 * math.sin(2 * math.radians(lambda_sun))
    
    # Declination of the sun
    sin_dec = math.sin(math.radians(lambda_sun)) * math.sin(math.radians(23.44))
    cos_dec = math.sqrt(1 - sin_dec**2)
    
    # Hour angle (for specified sun altitude)
    lat_rad = math.radians(lat)
    sun_alt_rad = math.radians(sun_altitude)
    
    cos_omega = (math.sin(sun_alt_rad) - math.sin(lat_rad) * sin_dec) / (math.cos(lat_rad) * cos_dec)
    
    # Check if sun reaches this altitude (polar regions might not)
    if cos_omega > 1:
        return "00:00"  # Sun never rises to this altitude
    elif cos_omega < -1:
        return "23:59"  # Sun never sets below this altitude
    
    omega = math.degrees(math.acos(cos_omega))
    
    # Time when sun reaches this altitude (setting)
    J_set = J_transit + omega / 360.0
    
    # Convert to local time
    # J_set is in UT, we need to add timezone offset
    sunset_hour = ((J_set - jd) * 24 + 12 + TIMEZONE_OFFSET) % 24
    
    hours = int(sunset_hour)
    minutes = int((sunset_hour - hours) * 60)
    
    return f"{hours:02d}:{minutes:02d}"

def fetch_coordinates_from_varastro(star_id: str, driver=None) -> tuple:
    """
    Fetch RA/Dec coordinates from var.astro.cz star page
    
    Args:
        star_id: The ID from the predictions table (integer as string)
        driver: Existing Selenium webdriver (optional, creates new one if not provided)
        
    Returns:
        Tuple of (ra_str, dec_str) or (None, None) if not found
    """
    close_driver = False
    if driver is None:
        # Create a new driver if none provided
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        close_driver = True
    
    try:
        # Navigate to star page
        star_url = f"https://var.astro.cz/en/Stars/{star_id}"
        driver.get(star_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Parse the page with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for RA/Dec in the page
        # The format on var.astro.cz is: "RA: 01h 22m 22.00s, DE: -29° 06' 54.00" (decimal)"
        ra_str = None
        dec_str = None
        
        import re
        page_text = soup.get_text()
        
        # Look for the pattern: RA: HHh MMm SS.SSs, DE: ±DD° MM' SS.SS"
        coord_pattern = r'RA:\s*(\d{1,2}h\s*\d{2}m\s*\d{2}(?:\.\d+)?s),\s*DE:\s*([+\-]?\d{1,2}°\s*\d{2}\'\s*\d{2}(?:\.\d+)?")'
        match = re.search(coord_pattern, page_text)
        
        if match:
            ra_raw = match.group(1)
            dec_raw = match.group(2)
            
            # Convert to standard format HH:MM:SS.SS
            ra_match = re.match(r'(\d{1,2})h\s*(\d{2})m\s*(\d{2}(?:\.\d+)?)s', ra_raw)
            if ra_match:
                ra_str = f"{ra_match.group(1)}:{ra_match.group(2)}:{ra_match.group(3)}"
            
            # Convert to standard format ±DD:MM:SS.SS
            dec_match = re.match(r'([+\-]?\d{1,2})°\s*(\d{2})\'\s*(\d{2}(?:\.\d+)?)"', dec_raw)
            if dec_match:
                dec_str = f"{dec_match.group(1)}:{dec_match.group(2)}:{dec_match.group(3)}"
        
        if ra_str and dec_str:
            logger.info(f"Fetched coordinates for star ID {star_id}: RA={ra_str}, Dec={dec_str}")
            return (ra_str, dec_str)
        else:
            logger.warning(f"Could not find RA/Dec on page for star ID {star_id}")
            # Log part of page content for debugging
            logger.debug(f"Page content sample: {page_text[:500]}")
            return (None, None)
            
    except Exception as e:
        logger.error(f"Error fetching coordinates for star ID {star_id}: {e}")
        return (None, None)
    finally:
        if close_driver and driver:
            driver.quit()

def lookup_coordinates_simbad(star_name: str, constellation: str = '') -> tuple:
    """
    Lookup RA/Dec coordinates for a star using SIMBAD
    
    Args:
        star_name: Star name (e.g., "V1812", "KQ", "RS Col", "V2759 Ori")
        constellation: Constellation abbreviation (e.g., "Aql", "Psc")
        
    Returns:
        Tuple of (ra_str, dec_str) or (None, None) if not found
    """
    try:
        # Build query name - try multiple strategies
        query_names = []
        
        # Guard against doubled constellation suffix (e.g., "EH Cnc Cnc" -> "EH Cnc")
        # This can happen if the scraper already combined name+constellation and then
        # the caller tries to append the constellation again.
        if constellation:
            double_suffix = f" {constellation} {constellation}"
            if star_name.strip().lower().endswith(f"{constellation.lower()} {constellation.lower()}"):
                star_name = star_name.strip()[: -len(f" {constellation}")].strip()
                logger.debug(f"Removed duplicate constellation suffix: now '{star_name}'")

        # Remove constellation suffix for survey stars with coordinate-based names
        # e.g., "ASAS  J042851-4035.3 Cae" -> "ASAS  J042851-4035.3"
        # But keep constellation for traditional variable stars like "V1123 Tau", "RS Col"
        cleaned_star_name = star_name
        if constellation:
            # Check if this is a survey star with coordinates (ASAS, OGLE, etc.)
            import re
            # Pattern: survey prefix followed by coordinates
            survey_pattern = r'^(ASAS|OGLE|CRTS|ATLAS|ZTF|Gaia|MASTER|TESS)\s+[BJ]?[\d\-\+\.: ]+$'
            
            # Check if star name ends with the constellation AND matches survey pattern
            if star_name.strip().lower().endswith(constellation.lower()):
                name_without_const = star_name.strip()[:-len(constellation)].strip()
                if re.match(survey_pattern, name_without_const, re.IGNORECASE):
                    cleaned_star_name = name_without_const
                    logger.debug(f"Removed constellation suffix from survey star '{star_name}' -> '{cleaned_star_name}'")
        
        # Special handling for NSV stars: "NSV 01105 For" -> "NSV01105"
        if cleaned_star_name.startswith('NSV '):
            # Extract the number and remove spaces
            nsv_compact = cleaned_star_name.replace(' ', '')  # "NSV01105For" or "NSV01105"
            # Try just NSV + number without constellation
            import re
            nsv_match = re.match(r'(NSV\d+)', nsv_compact)
            if nsv_match:
                query_names.append(nsv_match.group(1))  # "NSV01105"
        
        # Strategy 1: Use cleaned star_name (works for "RS Col", "V2759 Ori", "ASAS J042851-4035.3")
        query_names.append(cleaned_star_name)
        
        # Strategy 2: Add constellation if provided and not already in name
        if constellation and constellation.lower() not in cleaned_star_name.lower():
            query_names.append(f"{cleaned_star_name} {constellation}")
        
        # Try each query variation
        for query_name in query_names:
            try:
                logger.debug(f"Querying SIMBAD with: '{query_name}'")
                
                # Query SIMBAD - modern TAP API returns coordinates in degrees
                result_table = Simbad.query_object(query_name)
                
                if result_table is not None and len(result_table) > 0:
                    # Modern SIMBAD TAP returns 'ra' and 'dec' columns in degrees
                    if 'ra' in result_table.colnames and 'dec' in result_table.colnames:
                        ra_deg = float(result_table['ra'][0])
                        dec_deg = float(result_table['dec'][0])
                        
                        # Convert degrees to HH:MM:SS and DD:MM:SS using SkyCoord
                        coord_obj = SkyCoord(ra=ra_deg*u.degree, dec=dec_deg*u.degree)
                        ra_str = coord_obj.ra.to_string(unit=u.hour, sep=':', precision=2, pad=True)
                        dec_str = coord_obj.dec.to_string(unit=u.degree, sep=':', precision=1, pad=True, alwayssign=True)
                        
                        logger.info(f"Found coordinates for '{query_name}': RA={ra_str}, Dec={dec_str}")
                        return (ra_str, dec_str)
                    
                    # Fallback: try old format columns if they exist
                    elif 'RA' in result_table.colnames and 'DEC' in result_table.colnames:
                        ra = result_table['RA'][0]  # Format: "HH MM SS.ss"
                        dec = result_table['DEC'][0]  # Format: "+DD MM SS.s"
                        
                        # Convert to standard format
                        ra_str = ra.replace(' ', ':')
                        dec_str = dec.replace(' ', ':')
                        
                        logger.info(f"Found coordinates for '{query_name}': RA={ra_str}, Dec={dec_str}")
                        return (ra_str, dec_str)
                
            except Exception as e:
                logger.debug(f"Query failed for '{query_name}': {e}")
                continue
        
        logger.warning(f"Could not find coordinates for '{star_name}' (constellation: '{constellation}') after trying all strategies")
        return (None, None)
        
    except Exception as e:
        logger.error(f"Error in SIMBAD lookup for {star_name} {constellation}: {e}")
        return (None, None)

def calculate_altitude_at_time(ra_str: str, dec_str: str, obs_time: datetime, lat: float, lon: float) -> float:
    """
    Calculate altitude of a target at a given time using astropy
    
    Args:
        ra_str: Right ascension string (HH:MM:SS or decimal hours)
        dec_str: Declination string (+/-DD:MM:SS or decimal degrees)  
        obs_time: Observation time (datetime object)
        lat: Observer latitude in degrees
        lon: Observer longitude in degrees
        
    Returns:
        Altitude in degrees, or None if calculation fails
    """
    try:
        # Create observer location
        observer = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=0*u.m)
        
        # Parse RA - try different formats
        if ':' in str(ra_str):
            # Format like "HH:MM:SS"
            ra_parts = str(ra_str).strip().split(':')
            if len(ra_parts) == 3:
                ra_hours = float(ra_parts[0]) + float(ra_parts[1])/60 + float(ra_parts[2])/3600
            else:
                ra_hours = float(ra_parts[0]) + float(ra_parts[1])/60
            ra = ra_hours * u.hourangle
        else:
            # Decimal hours
            ra = float(ra_str) * u.hourangle
        
        # Parse Dec - try different formats
        if ':' in str(dec_str):
            # Format like "+/-DD:MM:SS"
            dec_str_clean = str(dec_str).strip().replace('+', '')
            dec_parts = dec_str_clean.split(':')
            if len(dec_parts) == 3:
                sign = -1 if dec_parts[0].startswith('-') else 1
                dec_deg = abs(float(dec_parts[0])) + float(dec_parts[1])/60 + float(dec_parts[2])/3600
                dec_deg *= sign
            else:
                dec_deg = float(dec_parts[0]) + float(dec_parts[1])/60
            dec = dec_deg * u.deg
        else:
            # Decimal degrees
            dec = float(dec_str) * u.deg
        
        # Create sky coordinate
        target_coord = SkyCoord(ra=ra, dec=dec, frame='icrs')
        
        # Convert observation time to astropy Time
        obs_time_astropy = Time(obs_time)
        
        # Create AltAz frame for this time and location
        altaz_frame = AltAz(obstime=obs_time_astropy, location=observer)
        
        # Transform to AltAz coordinates
        target_altaz = target_coord.transform_to(altaz_frame)
        
        return target_altaz.alt.degree
        
    except Exception as e:
        logger.debug(f"Could not calculate altitude for RA={ra_str}, Dec={dec_str}: {e}")
        return None

def check_altitude_during_observation(target: Dict, lat: float, lon: float, skip_lookup: bool = False) -> bool:
    """
    Check if target maintains sufficient altitude throughout observation window
    
    Uses astropy to calculate actual altitude at multiple points during the
    4-hour observation window (2 hours before to 2 hours after minima).
    
    Args:
        target: Target dictionary with minima time and RA/Dec coordinates
        lat: Observer latitude in degrees
        lon: Observer longitude in degrees
        skip_lookup: If True, skip coordinate lookups and use conservative check only
        
    Returns:
        True if target maintains >30° altitude throughout observation window
    """
    try:
        # Get RA/Dec coordinates
        ra = target.get('ra', '')
        dec = target.get('dec', '')
        
        # If no RA/Dec and skip_lookup is True, use conservative check
        if (not ra or not dec) and skip_lookup:
            altitude_str = target.get('altitude', '0')
            altitude = float(altitude_str)
            # Require 50° at minima if we can't calculate actual altitudes
            SAFE_ALTITUDE_AT_MINIMA = 50
            if altitude < SAFE_ALTITUDE_AT_MINIMA:
                logger.debug(f"{target.get('name', 'unknown')} altitude {altitude}° at minima - need >{SAFE_ALTITUDE_AT_MINIMA}° (skip_lookup=True)")
                return False
            return True
        
        # If no RA/Dec, try to lookup coordinates
        if not ra or not dec:
            star_name = target.get('name', '')
            constellation = target.get('constellation', '')
            
            # First try SIMBAD for standard variable star names (faster)
            # Only lookup for well-known stars (not catalog IDs starting with G, NSV, etc.)


            if star_name and not star_name.startswith(('G', 'NSV', 'CzeV', 'TYC')):
                logger.debug(f"Looking up coordinates from SIMBAD for {star_name} ({constellation})...")
                ra, dec = lookup_coordinates_simbad(star_name, constellation)
                
                if ra and dec:
                    # Cache the coordinates in the target
                    target['ra'] = ra
                    target['dec'] = dec
                    logger.info(f"Found coordinates for {star_name} ({constellation}): RA={ra}, Dec={dec}")
            
            # If SIMBAD didn't work, try var.astro.cz star page
            if not ra or not dec:
                star_id = target.get('id', '')
                if star_id:
                    logger.debug(f"Looking up coordinates from var.astro.cz for star ID {star_id} ({star_name})...")
                    ra, dec = fetch_coordinates_from_varastro(star_id)
                    
                    if ra and dec:
                        # Cache the coordinates in the target
                        target['ra'] = ra
                        target['dec'] = dec
                        logger.info(f"Found coordinates for ID {star_id} ({star_name}): RA={ra}, Dec={dec}")
        
        # If still no RA/Dec, fall back to conservative altitude check at minima
        if not ra or not dec:
            altitude_str = target.get('altitude', '0')
            altitude = float(altitude_str)
            # Require 50° at minima if we can't calculate actual altitudes
            SAFE_ALTITUDE_AT_MINIMA = 50
            if altitude < SAFE_ALTITUDE_AT_MINIMA:
                logger.debug(f"{target.get('name', 'unknown')} altitude {altitude}° at minima - need >{SAFE_ALTITUDE_AT_MINIMA}° (no RA/Dec for detailed calc)")

                return False
            return True
        
        # Check declination constraints
        try:
            # Parse declination from string format (e.g., "-50:02:36" or "-50°02'36\"")
            dec_str = dec.replace('°', ':').replace("'", ':').replace('"', '')
            dec_parts = dec_str.split(':')
            dec_degrees = float(dec_parts[0])
            if len(dec_parts) > 1:
                dec_minutes = float(dec_parts[1])
                dec_degrees += (dec_minutes / 60.0) * (1 if dec_degrees >= 0 else -1)
            if len(dec_parts) > 2:
                dec_seconds = float(dec_parts[2])
                dec_degrees += (dec_seconds / 3600.0) * (1 if dec_degrees >= 0 else -1)
            
            # Check if declination is within allowed range
            if dec_degrees < MIN_DECLINATION or dec_degrees > MAX_DECLINATION:
                logger.debug(f"{target.get('name', 'unknown')} declination {dec_degrees:.2f}° outside range [{MIN_DECLINATION}, {MAX_DECLINATION}]")
                return False
        except (ValueError, IndexError) as e:
            logger.debug(f"Could not parse declination '{dec}' for {target.get('name', 'unknown')}: {e}")
            # If we can't parse dec, continue with altitude checks
        
        # Parse minima time
        minima_time = parse_minima_time(target.get('minimum_time', ''))
        if not minima_time:
            return False
        
        # Check altitude every 30 minutes during observation window
        start_time = minima_time - timedelta(hours=2)
        end_time = minima_time + timedelta(hours=2)
        
        current_time = start_time
        min_altitude = float('inf')
        
        while current_time <= end_time:
            alt = calculate_altitude_at_time(ra, dec, current_time, lat, lon)
            
            if alt is None:
                # If calculation fails, fall back to conservative check
                altitude_str = target.get('altitude', '0')
                altitude = float(altitude_str)
                return altitude >= 50
            
            min_altitude = min(min_altitude, alt)
            
            if alt < MIN_ALTITUDE_DURING_OBS:
                logger.debug(f"{target.get('name', 'unknown')} drops to {alt:.1f}° at {current_time.strftime('%H:%M')} (< {MIN_ALTITUDE_DURING_OBS}°)")
                return False
            
            current_time += timedelta(minutes=30)
        
        logger.debug(f"{target.get('name', 'unknown')} minimum altitude during observation: {min_altitude:.1f}°")
        return True
        
    except Exception as e:
        logger.warning(f"Error checking altitude for {target.get('name', 'unknown')}: {e}")
        # Fall back to conservative check
        try:
            altitude_str = target.get('altitude', '0')
            altitude = float(altitude_str)
            return altitude >= 50
        except:
            return False

def format_target_display_name(target: Dict) -> str:
    """
    Format target name for display in logs.
    WDS targets (starting with 'G') show as: G1234.56789 (Constellation)
    Named variables already include constellation: CH Scl
    
    Args:
        target: Target dictionary with 'name' and 'constellation' keys
        
    Returns:
        Formatted target name string
    """
    name = target.get('name', '')
    constellation = target.get('constellation', '')
    
    # If name starts with 'G', it's a WDS catalog target - show constellation in parentheses
    if name.startswith('G') and constellation:
        return f"{name} ({constellation})"
    else:
        # Named variables already have constellation in the name (e.g., "CH Scl")
        return name

def select_targets_for_night(targets: List[Dict], dark_sky_time: str = None) -> List[Dict]:
    """
    Select optimal targets for the night based on timing and altitude constraints
    
    Timing strategy:
    - First target: minima at sun -15° altitude + 2 hours (allows 2hr pre-minima observation)
    - Second target: minima 4 hours after first target
    
    Args:
        targets: List of filtered target dictionaries
        dark_sky_time: Dark sky time as "HH:MM" string in LOCAL TIME (if None, will calculate for sun at -15°)
        
    Returns:
        List of selected targets for the night (usually 2)
    """
    # Calculate or parse dark sky time (local)
    today = date.today()
    
    if dark_sky_time is None:
        # Calculate when sun reaches -15° below horizon then add 2 hours for first target
        dark_sky_time = calculate_sunset_time(today, LATITUDE, LONGITUDE, sun_altitude=-15.0)
        logger.info(f"Calculated dark sky time (sun at -15°): {dark_sky_time} local")
        
        # First target should be dark sky + 2 hours
        dark_sky_local = datetime.combine(today, datetime.strptime(dark_sky_time, "%H:%M").time())
        first_target_local = dark_sky_local + timedelta(hours=2)
    else:
        # If dark_sky_time provided, add 2 hours for first target
        dark_sky_local = datetime.combine(today, datetime.strptime(dark_sky_time, "%H:%M").time())
        first_target_local = dark_sky_local + timedelta(hours=2)
    
    dark_sky_local = datetime.combine(today, datetime.strptime(dark_sky_time, "%H:%M").time())
    # Convert to UTC for comparison with target times
    first_target_utc = local_to_utc(first_target_local)
    
    logger.info(f"Dark sky time (sun at -15°) at {dark_sky_local.strftime('%H:%M')} local")
    logger.info(f"First target minima should be at {first_target_local.strftime('%H:%M')} local (dark sky + 2hrs)")
    logger.info(f"Second target minima should be at {(first_target_local + timedelta(hours=4)).strftime('%H:%M')} local (first + 4hrs)")
    logger.info(f"Looking for targets with minima around {first_target_local.strftime('%H:%M')} local time ({first_target_utc.strftime('%H:%M')} UTC)")
    
    selected_targets = []
    
    # Sort targets by minima time
    valid_targets = []
    dark_sky_time_only = dark_sky_local.time()  # Extract time component for comparison
    
    for target in targets:
        minima_time_utc = parse_minima_time(target.get('minimum_time', ''))
        if minima_time_utc:
            target['minima_datetime_utc'] = minima_time_utc
            target['minima_datetime_local'] = utc_to_local(minima_time_utc)
            
            # Calculate observation start time (2 hours before minima)
            obs_start_local = target['minima_datetime_local'] - timedelta(hours=2)
            obs_start_time_only = obs_start_local.time()  # Extract time component
            
            # Compare only the time of day, not the date
            # Allow starting within 15 minutes before dark sky as buffer
            buffer_time = (datetime.combine(date.today(), dark_sky_time_only) - timedelta(minutes=15)).time()
            
            if obs_start_time_only >= buffer_time or obs_start_time_only < datetime.strptime("06:00", "%H:%M").time():
                # Include if obs starts after buffer time, or in early morning (wrapped around midnight)
                valid_targets.append(target)
            else:
                logger.debug(f"Skipping {format_target_display_name(target)} - observation would start at {obs_start_time_only} before dark sky at {dark_sky_time_only}")
    
    logger.info(f"Found {len(valid_targets)} targets observable after dark sky")
    
    valid_targets.sort(key=lambda x: x['minima_datetime_utc'])
    
    # Find first target (closest to first_target_utc time, regardless of date)
    # We compare only the time (hour:minute), not the date
    first_target_hour = first_target_utc.hour + first_target_utc.minute / 60.0
    
    # Find all candidates within window and pick the closest
    first_target_candidates = []
    for target in valid_targets:
        target_hour = target['minima_datetime_utc'].hour + target['minima_datetime_utc'].minute / 60.0
        hour_diff = abs(target_hour - first_target_hour)
        
        # Find targets within a reasonable window (±30 minutes)
        if hour_diff < 0.5:  # Within 30 minutes
            # Check altitude during observation window (skip coordinate lookups for speed)
            if check_altitude_during_observation(target, LATITUDE, LONGITUDE, skip_lookup=True):
                first_target_candidates.append((target, hour_diff))
    
    # Sort by time difference and pick the closest
    if first_target_candidates:
        first_target_candidates.sort(key=lambda x: x[1])
        best_first_target = first_target_candidates[0][0]
        selected_targets.append(best_first_target)
        logger.info(f"Selected target 1: {format_target_display_name(best_first_target)} at {best_first_target['minima_datetime_local'].strftime('%H:%M')} local ({best_first_target['minimum_time']} UTC)")
        
        # Find second target (~4 hours after first)
        second_target_hour = (first_target_hour + TARGET_SPACING) % 24
        
        second_target_candidates = []
        for target in valid_targets:
            if target == best_first_target:
                continue
                
            second_hour = target['minima_datetime_utc'].hour + target['minima_datetime_utc'].minute / 60.0
            time_diff = abs(second_hour - second_target_hour)
            
            # Handle wrap-around midnight
            if time_diff > 12:
                time_diff = 24 - time_diff
            
            # Allow some flexibility (within 1 hour)
            if time_diff < 1.0:
                if check_altitude_during_observation(target, LATITUDE, LONGITUDE, skip_lookup=True):
                    second_target_candidates.append((target, time_diff))
        
        # Sort by time difference and pick the closest
        if second_target_candidates:
            second_target_candidates.sort(key=lambda x: x[1])
            best_second_target = second_target_candidates[0][0]
            selected_targets.append(best_second_target)
            logger.info(f"Selected target 2: {format_target_display_name(best_second_target)} at {best_second_target['minima_datetime_local'].strftime('%H:%M')} local ({best_second_target['minimum_time']} UTC)")
    
    # Now do detailed altitude checks with coordinate lookups for selected targets only
    logger.info("Performing detailed altitude checks for selected targets...")
    validated_targets = []
    rejected_targets = set()  # Keep track of rejected targets to avoid reselecting them
    
    for target in selected_targets:
        if check_altitude_during_observation(target, LATITUDE, LONGITUDE, skip_lookup=False):
            validated_targets.append(target)
            logger.info(f"Validated {target['name']} with detailed altitude calculations")
        else:
            logger.warning(f"Target {target['name']} failed detailed altitude check - will search for replacement")
            rejected_targets.add(target['name'])
    
    # If we don't have enough validated targets, try to find replacements
    MAX_TARGETS_PER_NIGHT = 2
    attempts = 0
    max_attempts = 20  # Prevent infinite loops
    
    # Track which time slots are filled vs empty
    target_slots = [None, None]  # [target1, target2] 
    
    # Fill existing validated targets into appropriate slots based on timing
    for target in validated_targets:
        target_hour = target['minima_datetime_utc'].hour + target['minima_datetime_utc'].minute / 60.0
        first_target_hour = first_target_utc.hour + first_target_utc.minute / 60.0
        second_target_hour = (first_target_hour + TARGET_SPACING) % 24
        
        # Determine which slot this target belongs to
        diff_to_first = abs(target_hour - first_target_hour)
        if diff_to_first > 12: diff_to_first = 24 - diff_to_first
        
        diff_to_second = abs(target_hour - second_target_hour)
        if diff_to_second > 12: diff_to_second = 24 - diff_to_second
        
        if diff_to_first <= diff_to_second:
            target_slots[0] = target  # First target slot
        else:
            target_slots[1] = target  # Second target slot
    
    while len([slot for slot in target_slots if slot is not None]) < MAX_TARGETS_PER_NIGHT and attempts < max_attempts:
        attempts += 1
        
        # Find which slot needs filling
        if target_slots[0] is None:
            slot_number = 1
            target_time_utc = first_target_utc
            search_window = 2.0  # hours (expanded from 1.0)
            logger.info(f"Searching for replacement target {slot_number} (attempt {attempts})...")
        elif target_slots[1] is None:
            slot_number = 2
            # Use first validated target's time + spacing
            first_minima = target_slots[0]['minima_datetime_utc']
            target_time_utc = first_minima + timedelta(hours=TARGET_SPACING)
            search_window = 3.0  # hours (expanded from 1.5 for wider second target search)
            logger.info(f"Searching for replacement target {slot_number} (attempt {attempts})...")
        else:
            break  # Both slots filled
        
        logger.info(f"Searching in {search_window:.1f} hour window around {target_time_utc.strftime('%H:%M')} UTC")
        
        # Find candidates
        target_hour = target_time_utc.hour + target_time_utc.minute / 60.0
        candidates = []
        
        for target in valid_targets:
            # Skip already validated or rejected targets
            if target['name'] in rejected_targets or target in target_slots:
                continue
            
            candidate_hour = target['minima_datetime_utc'].hour + target['minima_datetime_utc'].minute / 60.0
            time_diff = abs(candidate_hour - target_hour)
            
            # Handle wrap-around midnight
            if time_diff > 12:
                time_diff = 24 - time_diff
            
            if time_diff < search_window:
                # Quick altitude check first
                if check_altitude_during_observation(target, LATITUDE, LONGITUDE, skip_lookup=True):
                    candidates.append((target, time_diff))
        
        if not candidates:
            logger.warning(f"No more candidate targets found in search window of {search_window:.1f} hours")
            # Expand search window for next attempt
            search_window += 1.0
            logger.info(f"Expanding search window to {search_window:.1f} hours for next attempt")
            continue
        
        # Sort by time difference and try candidates in order
        candidates.sort(key=lambda x: x[1])
        found_valid = False
        
        for candidate, time_diff in candidates:
            # Detailed check with coordinate lookup
            if check_altitude_during_observation(candidate, LATITUDE, LONGITUDE, skip_lookup=False):
                target_slots[slot_number - 1] = candidate  # Assign to correct slot
                logger.info(f"Found replacement target {slot_number}: {candidate['name']} ({candidate.get('constellation', '')}) at {candidate['minima_datetime_local'].strftime('%H:%M')} local ({candidate['minimum_time']} UTC)")
                found_valid = True
                break
            else:
                rejected_targets.add(candidate['name'])
                logger.debug(f"Candidate {candidate['name']} rejected")
        
        if not found_valid:
            logger.warning(f"All candidate targets failed validation")
            # Widen search window for next attempt (more aggressive expansion)
            search_window += 1.0  # Increased from 0.5 to 1.0 hours per attempt
    
    # Convert filled slots back to validated_targets list
    validated_targets = [target for target in target_slots if target is not None]
    
    if len(validated_targets) < MAX_TARGETS_PER_NIGHT:
        logger.warning(f"Only found {len(validated_targets)} valid targets (wanted {MAX_TARGETS_PER_NIGHT})")
    
    return validated_targets[:MAX_TARGETS_PER_NIGHT]

def parse_datatable_json(data: dict) -> List[Dict]:
    """
    Parse DataTables JSON response to extract target information
    
    Args:
        data: JSON response from the DataTables AJAX endpoint
        
    Returns:
        List of target dictionaries
    """
    targets = []
    
    if 'data' in data:
        for row in data['data']:
            # DataTables returns an array for each row
            # Based on the table headers: ID, Entries, Name, Constellation, P/S, MagMax, MagMin, Band, Type, MinTime, Alt, Az, D, Moon%, MoonDist, SunAlt, Period, CrossId, RA, Dec
            if len(row) >= 10:
                target = {
                    'id': row[0] if len(row) > 0 else '',
                    'name': row[2] if len(row) > 2 else '',
                    'constellation': row[3] if len(row) > 3 else '',
                    'minima_type': row[4] if len(row) > 4 else '',
                    'mag_max': row[5] if len(row) > 5 else '',
                    'mag_min': row[6] if len(row) > 6 else '',
                    'band': row[7] if len(row) > 7 else '',
                    'variability_type': row[8] if len(row) > 8 else '',
                    'minimum_time': row[9] if len(row) > 9 else '',
                    'altitude': row[10] if len(row) > 10 else '',
                    'azimuth': row[11] if len(row) > 11 else '',
                    'duration_hours': row[12] if len(row) > 12 else '',
                    'period': row[16] if len(row) > 16 else '',
                    'ra': row[18] if len(row) > 18 else '',
                    'dec': row[19] if len(row) > 19 else ''
                }
                targets.append(target)
                logger.debug(f"Found target: {target['name']}")

    return targets

def parse_json_targets(data: dict) -> List[Dict]:
    """
    Parse JSON response to extract target information
    
    Args:
        data: JSON response from the API
        
    Returns:
        List of target dictionaries
    """
    targets = []
    
    if 'data' in data:
        for item in data['data']:
            target = {
                'name': item.get('name', ''),

                'constellation': item.get('constellation', ''),

                'minimum_time': item.get('minimumTime', ''),

                'mag_max': item.get('magMax', ''),

                'mag_min': item.get('magMin', ''),

                'altitude': item.get('altitude', ''),

                'azimuth': item.get('azimuth', ''),

                'period': item.get('period', ''),

                'ra': item.get('ra', ''),

                'dec': item.get('dec', '')
            }
            targets.append(target)
            logger.debug(f"Found target: {target['name']}")
    
    return targets

def export_to_nina_format(targets: List[Dict], output_path: Path = None):
    """
    Export targets to NINA scheduling format
    
    Args:
        targets: List of target dictionaries
        output_path: Path to save the output file
    """
    if output_path is None:
        output_path = Path(__file__).parent / f"targets_{date.today()}.csv"
    
    logger.info(f"Exporting {len(targets)} targets to {output_path}")
    
    # Export as CSV with relevant columns for NINA
    import csv
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            'ID',
            'Name', 
            'Constellation',
            'RA',
            'Dec',
            'Minimum Time (UTC)', 
            'Magnitude Max', 
            'Magnitude Min',
            'Altitude (°)',
            'Minima Type',
            'Band',
            'Variability Type'
        ])
        
        # Write data rows
        for target in targets:
            writer.writerow([
                target.get('id', ''),

                target.get('name', ''),

                target.get('constellation', ''),

                target.get('ra', ''),

                target.get('dec', ''),

                target.get('minimum_time', ''),

                target.get('mag_max', ''),

                target.get('mag_min', ''),

                target.get('altitude', ''),

                target.get('minima_type', ''),

                target.get('band', ''),

                target.get('variability_type', '')
            ])
    
    logger.info(f"Export complete: {output_path}")
    
    # Also save as JSON for easier programmatic access
    # Remove datetime objects that aren't JSON serializable
    json_targets = []
    for target in targets:
        json_target = {k: v for k, v in target.items() 
                      if k not in ['minima_datetime_utc', 'minima_datetime_local']}
        json_targets.append(json_target)
    
    json_path = output_path.with_suffix('.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_targets, f, indent=2, ensure_ascii=False)
    logger.info(f"Also saved JSON version: {json_path}")


def prompt_s50_exposure_override() -> tuple[bool, float]:
    """
    Show dialog to override S50 default exposure time
    
    Returns:
        Tuple of (use_override: bool, exposure_time: float)
    """
    logger.info("Showing S50 exposure time override dialog...")
    
    # Try to get existing Tk root, or create one if needed
    try:
        root = tk._default_root
        if root is None:
            root = tk.Tk()
            root.withdraw()
            created_root = True
        else:
            created_root = False
    except:
        root = tk.Tk()
        root.withdraw()
        created_root = True
    
    dialog = tk.Toplevel(root)
    dialog.title("S50 Exposure Time Override")
    dialog.geometry("400x180")
    dialog.resizable(False, False)
    
    # Make dialog modal and bring to front
    dialog.lift()
    dialog.focus_force()
    dialog.attributes('-topmost', True)
    dialog.after(100, lambda: dialog.attributes('-topmost', False))
    dialog.grab_set()
    
    result = {'override': False, 'exposure_time': 10.0}
    
    # Main message
    tk.Label(dialog, text="Override standard 10\" exptime?", 
             font=('Arial', 12, 'bold'), pady=10).pack()
    
    tk.Label(dialog, text="Default: 10 seconds for S50 telescope",
             font=('Arial', 9), fg='gray').pack()
    
    # Exposure time entry frame
    entry_frame = tk.Frame(dialog, pady=10)
    entry_frame.pack()
    
    tk.Label(entry_frame, text="Exposure time (seconds):", 
             font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
    
    exp_var = tk.StringVar(value="10")
    exp_entry = tk.Entry(entry_frame, textvariable=exp_var, width=10, 
                         font=('Arial', 10))
    exp_entry.pack(side=tk.LEFT, padx=5)
    exp_entry.select_range(0, tk.END)
    exp_entry.focus()
    
    # Button frame
    button_frame = tk.Frame(dialog, pady=10)
    button_frame.pack()
    
    def on_yes():
        try:
            exp_time = float(exp_var.get())
            if exp_time <= 0:
                messagebox.showerror("Invalid Input", "Exposure time must be positive")
                return
            result['override'] = True
            result['exposure_time'] = exp_time
            dialog.destroy()
            if created_root:
                root.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number")
    
    def on_no():
        result['override'] = False
        result['exposure_time'] = 10.0
        dialog.destroy()
        if created_root:
            root.destroy()
    
    tk.Button(button_frame, text="Yes - Use Custom", command=on_yes, 
              width=15, bg='#4CAF50', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
    tk.Button(button_frame, text="No - Use Default (10s)", command=on_no, 
              width=18, bg='#888', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Wait for dialog to close
    dialog.wait_window()
    
    return result['override'], result['exposure_time']


def export_to_nina_json(targets: List[Dict], output_dir: Path = None, template_file: str = None, mode: str = "individual", telescope: str = None):
    """
    Export targets to NINA JSON format using a template
    
    Args:
        targets: List of target dictionaries
        output_dir: Directory to save the JSON files (default: NINA VarStars directory with date)
        template_file: Path to template JSON file (default: NINA_TEMPLATE_FILE config, or VarStarS50.template.json for S50)
        mode: Export mode - "individual" for separate files per target, "night_sequence" for single night sequence
        telescope: Telescope type ('SCT' or 'S50') - determines which template to use if template_file not specified
    
    Returns:
        List of created file paths for individual mode, single file path for night_sequence mode, or None if failed
    """
    if mode == "night_sequence":
        return export_to_nina_night_sequence(targets, output_dir, template_file, telescope=telescope)
    
    # Continue with original individual file export logic
    if output_dir is None:
        # Create date-based directory structure using configurable base path
        today = date.today()
        date_str = today.strftime('%Y%m%d')  # Format: 20251102
        telescope_dir = telescope if telescope else "SCT"
        output_dir = Path(NINA_EXPORT_BASE_DIR).parent / "VarStars" / telescope_dir / date_str
    else:
        # Convert string to Path object if needed
        output_dir = Path(output_dir)
        
    # Always ensure the output directory exists (whether default or custom)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    
    if template_file is None:
        # Select template based on telescope type
        if telescope == "S50":
            template_file = "VarStarS50.template.json"
            logger.info(f"Using S50 template for telescope type: {telescope}")
        else:
            template_file = "VarStarSCT.template.json"
            logger.info(f"Using SCT template for telescope type: {telescope}")
    
    # Load template
    template_path = Path(__file__).parent / template_file
    if not template_path.exists():
        logger.error(f"Template file not found: {template_path}")
        logger.error("Please ensure the template file exists or update NINA_TEMPLATE_FILE configuration")
        return
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        logger.info(f"Loaded NINA template from {template_path}")
    except Exception as e:
        logger.error(f"Failed to load template file: {e}")
        return
    
    logger.info(f"Exporting {len(targets)} targets to NINA JSON format in {output_dir}")
    
    # For S50, ask user about exposure time override
    s50_exposure_override = None
    logger.info(f"Telescope type: '{telescope}' (checking for S50 override)")
    if telescope == "S50":
        logger.info("Telescope is S50 - prompting for exposure time override")
        use_override, custom_exptime = prompt_s50_exposure_override()
        if use_override:
            s50_exposure_override = custom_exptime
            logger.info(f"S50 exposure override: using {custom_exptime}s instead of default 10s")
        else:
            logger.info(f"S50 exposure: using default 10s")
    else:
        logger.info(f"Telescope is not S50 (it's '{telescope}'), skipping exposure override")
    
    created_files = []  # Track created files for return value
    
    # Log each target name for debugging
    target_names = [t.get('name', 'Unknown') for t in targets]
    logger.info(f"Target list: {', '.join(target_names)}")

    def _normalize_nina_ids(obj: Any) -> Any:
        """
        Ensure all "$id" values are unique and "$ref" references updated.
        This walks the nested structure, collects $id values in encounter order,
        assigns new sequential numeric ids as strings, and replaces all $id and
        $ref occurrences. This prevents duplicate id problems that some NINA
        installations reject.
        
        This function ensures complete uniqueness by:
        1. Assigning a unique ID to every object with $id based on Python object identity
        2. Mapping old $id values to new ones for $ref resolution
        3. Removing any $id from objects that are newly created or duplicated
        """
        # First pass: collect all objects that currently have $id
        # and assign them brand new sequential IDs
        mapping_by_obj = {}
        first_new_for_old = {}
        next_id = 1

        def assign(o):
            nonlocal next_id
            if isinstance(o, dict):
                if "$id" in o:
                    old = o["$id"]
                    new = str(next_id)
                    # Use object identity to track unique objects
                    obj_id = id(o)
                    # Only assign if we haven't seen this exact object before
                    if obj_id not in mapping_by_obj:
                        mapping_by_obj[obj_id] = new
                        # Track the first new ID for each old ID value (for $ref mapping)
                        if old not in first_new_for_old:
                            first_new_for_old[old] = new
                        next_id += 1
                for v in o.values():
                    assign(v)
            elif isinstance(o, list):
                for v in o:
                    assign(v)

        assign(obj)

        def replace(o):
            if isinstance(o, dict):
                if "$id" in o:
                    obj_id = id(o)
                    if obj_id in mapping_by_obj:
                        o["$id"] = mapping_by_obj[obj_id]
                    else:
                        # This object has $id but wasn't in our mapping
                        # This shouldn't happen, but if it does, remove the $id
                        # to prevent conflicts
                        logger.warning(f"Found object with $id but no mapping: {o.get('$type', 'unknown')}")
                        del o["$id"]
                if "$ref" in o:
                    oldref = o["$ref"]
                    if oldref in first_new_for_old:
                        o["$ref"] = first_new_for_old[oldref]
                    else:
                        # Reference to an ID that doesn't exist - this is an error
                        logger.warning(f"Found $ref to non-existent ID: {oldref}")
                for v in o.values():
                    replace(v)
            elif isinstance(o, list):
                for v in o:
                    replace(v)

        replace(obj)
        return obj
    
    for i, target in enumerate(targets):
        target_name = target.get('name', 'Unknown')
        logger.info(f"Processing target {i+1}/{len(targets)}: {target_name}")
        ra_str = target.get('ra', '00:00:00')
        dec_str = target.get('dec', '+00:00:00')
        minima_time = target.get('minimum_time', '')
        is_last_target = (i == len(targets) - 1)  # Check if this is the last target
        
        # Parse RA (HH:MM:SS.SS format)
        ra_parts = ra_str.split(':')
        ra_hours = int(ra_parts[0]) if len(ra_parts) > 0 and ra_parts[0].strip() else 0
        ra_minutes = int(ra_parts[1]) if len(ra_parts) > 1 and ra_parts[1].strip() else 0
        ra_seconds = float(ra_parts[2]) if len(ra_parts) > 2 and ra_parts[2].strip() else 0.0
        
        # Parse Dec (±DD:MM:SS.SS format)
        dec_negative = dec_str.startswith('-')
        dec_str_abs = dec_str.lstrip('+-')
        dec_parts = dec_str_abs.split(':')
        dec_degrees = int(dec_parts[0]) if len(dec_parts) > 0 and dec_parts[0].strip() else 0
        # Keep the negative sign on dec_degrees if declination is negative
        if dec_negative:
            dec_degrees = -dec_degrees
        dec_minutes = int(dec_parts[1]) if len(dec_parts) > 1 and dec_parts[1].strip() else 0
        dec_seconds = float(dec_parts[2]) if len(dec_parts) > 2 and dec_parts[2].strip() else 0.0
        
        # Parse minima time to get observation start and end times
        minima_datetime = target.get('minima_datetime_local')
        if minima_datetime:
            # Start 2 hours before minima
            start_time = minima_datetime - timedelta(hours=2)
            start_hours = start_time.hour
            start_minutes = start_time.minute
            
            if is_last_target:
                # For the last target, set end time to astronomical dawn
                obs_date = minima_datetime.date()
                dawn_time_str = calculate_astronomical_dawn(obs_date, LATITUDE, LONGITUDE)
                dawn_parts = dawn_time_str.split(':')
                end_hours = int(dawn_parts[0])
                end_minutes = int(dawn_parts[1])
                logger.info(f"Last target {target_name}: end time set to astronomical dawn at {dawn_time_str}")
            else:
                # End 2 hours AFTER minima (not start + fixed window)
                end_time = minima_datetime + timedelta(hours=2)
                end_hours = end_time.hour
                end_minutes = end_time.minute
        else:
            # Default to 20:00 if no time available
            start_hours = 20
            start_minutes = 0
            if is_last_target:
                # For last target with no minima time, use astronomical dawn
                today = date.today()
                dawn_time_str = calculate_astronomical_dawn(today, LATITUDE, LONGITUDE)
                dawn_parts = dawn_time_str.split(':')
                end_hours = int(dawn_parts[0])
                end_minutes = int(dawn_parts[1])
            else:
                end_hours = 0
                end_minutes = 0
        
        # Calculate exposure time based on magnitude (or use fixed 10s for S50)
        if telescope == "S50":
            if s50_exposure_override is not None:
                exposure_time = s50_exposure_override
                logger.info(f"Target {target_name}: Using custom S50 exposure time: {exposure_time}s")
            else:
                exposure_time = 10
                logger.info(f"Target {target_name}: Using default S50 exposure time: {exposure_time}s")
        else:
            mag_max_str = target.get('mag_max', '12.0')
            try:
                mag_max = float(mag_max_str)
                # Use instrument-specific exposure time scaling
                instrument = telescope if telescope in ['SCT', 'S50'] else 'SCT'
                exposure_time = get_exposure_time(mag_max, instrument=instrument)
                logger.info(f"Target {target_name}: mag_max={mag_max}, exposure_time={exposure_time}s (instrument={instrument})")
            except (ValueError, TypeError):
                exposure_time = 40.0  # Default fallback
                logger.warning(f"Could not parse magnitude for {target_name}, using default exposure time {exposure_time}s")
        
        # Create a deep copy of the template for this target
        import copy
        nina_json = copy.deepcopy(template)
        
        # Helper function to recursively update coordinates in the template
        def update_coordinates(obj, ra_h, ra_m, ra_s, dec_neg, dec_d, dec_m, dec_s):
            """Recursively find and update InputCoordinates in the JSON structure"""
            if isinstance(obj, dict):
                if obj.get("$type") == "NINA.Astrometry.InputCoordinates, NINA.Astrometry":
                    obj["RAHours"] = ra_h
                    obj["RAMinutes"] = ra_m
                    obj["RASeconds"] = ra_s
                    obj["NegativeDec"] = dec_neg
                    obj["DecDegrees"] = dec_d
                    obj["DecMinutes"] = dec_m
                    obj["DecSeconds"] = dec_s
                else:
                    for value in obj.values():
                        update_coordinates(value, ra_h, ra_m, ra_s, dec_neg, dec_d, dec_m, dec_s)
            elif isinstance(obj, list):
                for item in obj:
                    update_coordinates(item, ra_h, ra_m, ra_s, dec_neg, dec_d, dec_m, dec_s)
        
        # Helper function to update END time condition (in Target Imaging Instructions container)
        # This is actually the loop end time, not the start time as previously thought
        def update_end_time_condition(obj, hours, minutes):
            """Find and update TimeCondition in SequentialContainer for end time"""
            if isinstance(obj, dict):
                # Look for SequentialContainer with name "Target Imaging Instructions"
                if (obj.get("$type") == "NINA.Sequencer.Container.SequentialContainer, NINA.Sequencer" and 
                    obj.get("Name") == "Target Imaging Instructions"):
                    conditions = obj.get("Conditions", {})
                    values = conditions.get("$values", [])
                    
                    # Update TimeCondition in this container
                    for condition in values:
                        if condition.get("$type") == "NINA.Sequencer.Conditions.TimeCondition, NINA.Sequencer":
                            condition["Hours"] = hours
                            condition["Minutes"] = minutes
                            logger.debug(f"Set end time condition: {hours:02d}:{minutes:02d}")
                else:
                    for value in obj.values():
                        update_end_time_condition(value, hours, minutes)
            elif isinstance(obj, list):
                for item in obj:
                    update_end_time_condition(item, hours, minutes)
        
        # Helper function to update exposure time
        def update_exposure_time(obj, exp_time):
            """Recursively find and update TakeExposure ExposureTime in the JSON structure"""
            if isinstance(obj, dict):
                if obj.get("$type") == "NINA.Sequencer.SequenceItem.Imaging.TakeExposure, NINA.Sequencer":
                    obj["ExposureTime"] = exp_time
                else:
                    for value in obj.values():
                        update_exposure_time(value, exp_time)
            elif isinstance(obj, list):
                for item in obj:
                    update_exposure_time(item, exp_time)
        
        # Helper function to update loop condition and add time-based end condition
        def update_loop_until_time(obj, end_hours, end_minutes):
            """
            Update LoopCondition to 1 iteration and add TimeCondition to SmartExposure 
            conditions ONLY (not modifying existing TimeConditions elsewhere).
            """
            if isinstance(obj, dict):
                # Look for SmartExposure specifically
                if obj.get("$type") == "NINA.Sequencer.SequenceItem.Imaging.SmartExposure, NINA.Sequencer":
                    # Found SmartExposure, now look for its Conditions
                    conditions = obj.get("Conditions", {})

                    values = conditions.get("$values", [])
                    
                    # Find and update the LoopCondition
                    for condition in values:
                        if condition.get("$type") == "NINA.Sequencer.Conditions.LoopCondition, NINA.Sequencer":
                            # Set to 1 iteration per loop cycle
                            condition["Iterations"] = 1
                            condition["CompletedIterations"] = 0
                    
                    # Check if we already have an end time condition in SmartExposure
                    has_end_time_condition = any(
                        condition.get("$type") == "NINA.Sequencer.Conditions.TimeCondition, NINA.Sequencer" 
                        and condition.get("Hours") == end_hours 
                        and condition.get("Minutes") == end_minutes
                        for condition in values
                    )
                    
                    if not has_end_time_condition:
                        # Create a new TimeCondition for the end time IN SMARTEXPOSURE CONDITIONS ONLY
                        end_time_condition = {
                            "$id": str(len(values) + 1000),  # Unique ID
                            "$type": "NINA.Sequencer.Conditions.TimeCondition, NINA.Sequencer",
                            "Hours": end_hours,
                            "Minutes": end_minutes,
                            "Seconds": 0,
                            "DateTime": None,
                            "Parent": None,
                            "IsEnabled": True
                        }
                        values.append(end_time_condition)
                        logger.debug(f"Added end time condition to SmartExposure: {end_hours:02d}:{end_minutes:02d}")
                else:
                    # Continue searching but don't modify any existing TimeConditions
                    for value in obj.values():
                        update_loop_until_time(value, end_hours, end_minutes)
            elif isinstance(obj, list):
                for item in obj:
                    update_loop_until_time(item, end_hours, end_minutes)
        
        # Helper function to update center after drift tolerance
        def update_center_after_drift(obj, distance_arcmin):
            """Recursively find and update CenterAfterDriftTrigger distance"""
            if isinstance(obj, dict):
                if obj.get("$type") == "NINA.Sequencer.Trigger.Platesolving.CenterAfterDriftTrigger, NINA.Sequencer":
                    obj["DistanceArcMinutes"] = distance_arcmin
                else:
                    for value in obj.values():
                        update_center_after_drift(value, distance_arcmin)
            elif isinstance(obj, list):
                for item in obj:
                    update_center_after_drift(item, distance_arcmin)
        
        # Helper function to update Pushover message for last target
        def update_pushover_message(obj, title, message):
            """Recursively find and update SendToPushover title and message"""
            if isinstance(obj, dict):
                if obj.get("$type") == "DaleGhent.NINA.GroundStation.SendToPushover.SendToPushover, DaleGhent.NINA.GroundStation":
                    # Only update the one with "done" in the title (not the safety ones)
                    if "$$TARGET_NAME$$" in obj.get("Title", ""):
                        obj["Title"] = title
                        obj["Message"] = message
                        logger.debug(f"Updated Pushover: {title} - {message}")
                else:
                    for value in obj.values():
                        update_pushover_message(value, title, message)
            elif isinstance(obj, list):
                for item in obj:
                    update_pushover_message(item, title, message)
        
        # Update top-level target information
        if "Target" in nina_json:
            nina_json["Target"]["TargetName"] = target_name
        nina_json["Name"] = target_name
        
        # Update all coordinates in the template
        update_coordinates(nina_json, ra_hours, ra_minutes, ra_seconds, dec_negative, dec_degrees, dec_minutes, dec_seconds)
        
        # Update END time condition (observation end time) in Target Imaging Instructions container
        update_end_time_condition(nina_json, end_hours, end_minutes)
        
        # Update loop condition and END time (will loop until manually stopped or other conditions met)
        if minima_datetime:
            update_loop_until_time(nina_json, end_hours, end_minutes)
        
        # Update exposure time
        update_exposure_time(nina_json, exposure_time)
        
        # Update center after drift tolerance
        update_center_after_drift(nina_json, CENTER_AFTER_DRIFT_ARCMIN)
        
        # Update Pushover message for last target
        if is_last_target:
            update_pushover_message(nina_json, "$$TARGET_NAME$$ done", "done for the night")
            logger.info(f"Updated Pushover message for last target: {target_name}")
        
        
        # Save to file
        filename = f"{target_name.replace('/', '_')}.json"
        filepath = output_dir / filename
        
        # Normalize $id and $ref values to ensure uniqueness and validity
        nina_json = _normalize_nina_ids(nina_json)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(nina_json, f, indent=2, ensure_ascii=False)
        
        created_files.append(filepath)  # Add to list of created files
        logger.info(f"Created NINA target file: {filepath}")
    
    logger.info(f"Exported {len(targets)} NINA JSON files")
    return created_files  # Return list of created files


def export_to_nina_night_sequence(targets: List[Dict], output_dir: Path = None, template_file: str = None, night_template_file: str = None, telescope: str = None):
    """
    Export targets to a single NINA night sequence JSON format
    
    Args:
        targets: List of target dictionaries
        output_dir: Directory to save the JSON file (default: NINA VarStars directory with date)
        template_file: Path to individual target template JSON file (default: NINA_TEMPLATE_FILE config, or VarStarS50.template.json for S50)
        night_template_file: Path to night sequence template JSON file (default: night_sequence.template.json)
        telescope: Telescope type ('SCT' or 'S50') - determines which template to use if template_file not specified
    
    Returns:
        Path to created night sequence file, or None if failed
    """
    if output_dir is None:
        # Create date-based directory structure using configurable base path
        today = date.today()
        date_str = today.strftime('%Y%m%d')  # Format: 20251102
        telescope_dir = telescope if telescope else "SCT"
        output_dir = Path(NINA_EXPORT_BASE_DIR).parent / "Sequences" / telescope_dir / date_str
        
    # Always ensure the output directory exists (whether default or custom)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")
    
    if template_file is None:
        # Select template based on telescope type
        if telescope == "S50":
            template_file = "VarStarS50.template.json"
            logger.info(f"Using S50 template for telescope type: {telescope}")
        else:
            template_file = "VarStarSCT.template.json"
            logger.info(f"Using SCT template for telescope type: {telescope}")
    if night_template_file is None:
        night_template_file = "night_sequence_complex.json"
    
    # Load individual target template - handle both relative and absolute paths
    if Path(template_file).is_absolute():
        target_template_path = Path(template_file)
    else:
        target_template_path = Path(__file__).parent / template_file
    
    if not target_template_path.exists():
        logger.error(f"Target template file not found: {target_template_path}")
        return None

    # Load night sequence template - handle both relative and absolute paths  
    if Path(night_template_file).is_absolute():
        night_template_path = Path(night_template_file)
    else:
        night_template_path = Path(__file__).parent / night_template_file
    if not night_template_path.exists():
        logger.error(f"Night template file not found: {night_template_path}")
        return None
    
    try:
        with open(target_template_path, 'r', encoding='utf-8') as f:
            target_template = json.load(f)
        with open(night_template_path, 'r', encoding='utf-8') as f:
            night_template = json.load(f)
        logger.info(f"Loaded templates from {target_template_path} and {night_template_path}")
    except Exception as e:
        logger.error(f"Failed to load template files: {e}")
        return None
    
    logger.info(f"Generating night sequence with {len(targets)} targets")
    
    # For S50, ask user about exposure time override
    s50_exposure_override = None
    if telescope == "S50":
        use_override, custom_exptime = prompt_s50_exposure_override()
        if use_override:
            s50_exposure_override = custom_exptime
            logger.info(f"S50 exposure override: using {custom_exptime}s instead of default 10s")
        else:
            logger.info(f"S50 exposure: using default 10s")

    # Helper function to normalize IDs (reuse from existing function)
    def _normalize_nina_ids(obj: Any) -> Any:
        """Ensure all "$id" values are unique and "$ref" references updated."""
        mapping_by_obj = {}
        first_new_for_old = {}
        next_id = 1

        def assign(o):
            nonlocal next_id
            if isinstance(o, dict):
                if "$id" in o:
                    old = o["$id"]
                    new = str(next_id)
                    obj_id = id(o)
                    if obj_id not in mapping_by_obj:
                        mapping_by_obj[obj_id] = new
                        if old not in first_new_for_old:
                            first_new_for_old[old] = new
                        next_id += 1
                for v in o.values():
                    assign(v)
            elif isinstance(o, list):
                for v in o:
                    assign(v)

        assign(obj)

        def replace(o):
            if isinstance(o, dict):
                if "$id" in o:
                    obj_id = id(o)
                    if obj_id in mapping_by_obj:
                        o["$id"] = mapping_by_obj[obj_id]
                    else:
                        logger.warning(f"Found object with $id but no mapping: {o.get('$type', 'unknown')}")
                        del o["$id"]
                if "$ref" in o:
                    oldref = o["$ref"]
                    if oldref in first_new_for_old:
                        o["$ref"] = first_new_for_old[oldref]
                    else:
                        logger.warning(f"Found $ref to non-existent ID: {oldref}")
                for v in o.values():
                    replace(v)
            elif isinstance(o, list):
                for v in o:
                    replace(v)

        replace(obj)
        return obj

    # Helper functions from original export function
    def update_coordinates(obj, ra_h, ra_m, ra_s, dec_neg, dec_d, dec_m, dec_s):
        """Recursively find and update InputCoordinates in the JSON structure"""
        if isinstance(obj, dict):
            if obj.get("$type") == "NINA.Astrometry.InputCoordinates, NINA.Astrometry":
                obj["RAHours"] = ra_h
                obj["RAMinutes"] = ra_m
                obj["RASeconds"] = ra_s
                obj["NegativeDec"] = dec_neg
                obj["DecDegrees"] = dec_d
                obj["DecMinutes"] = dec_m
                obj["DecSeconds"] = dec_s
            else:
                for value in obj.values():
                    update_coordinates(value, ra_h, ra_m, ra_s, dec_neg, dec_d, dec_m, dec_s)
        elif isinstance(obj, list):
            for item in obj:
                update_coordinates(item, ra_h, ra_m, ra_s, dec_neg, dec_d, dec_m, dec_s)

    def update_exposure_time(obj, exp_time):
        """Recursively find and update TakeExposure ExposureTime in the JSON structure"""
        if isinstance(obj, dict):
            if obj.get("$type") == "NINA.Sequencer.SequenceItem.Imaging.TakeExposure, NINA.Sequencer":
                obj["ExposureTime"] = exp_time
            else:
                for value in obj.values():
                    update_exposure_time(value, exp_time)
        elif isinstance(obj, list):
            for item in obj:
                update_exposure_time(item, exp_time)

    def update_end_time_condition(obj, hours, minutes):
        """Find and update TimeCondition in SequentialContainer for end time"""
        if isinstance(obj, dict):
            if (obj.get("$type") == "NINA.Sequencer.Container.SequentialContainer, NINA.Sequencer" and 
                obj.get("Name") == "Target Imaging Instructions"):
                conditions = obj.get("Conditions", {})
                values = conditions.get("$values", [])
                
                for condition in values:
                    if condition.get("$type") == "NINA.Sequencer.Conditions.TimeCondition, NINA.Sequencer":
                        condition["Hours"] = hours
                        condition["Minutes"] = minutes
                        logger.debug(f"Set end time condition: {hours:02d}:{minutes:02d}")
            else:
                for value in obj.values():
                    update_end_time_condition(value, hours, minutes)
        elif isinstance(obj, list):
            for item in obj:
                update_end_time_condition(item, hours, minutes)

    # Create a deep copy of the night template
    import copy
    night_sequence = copy.deepcopy(night_template)
    
    # Update sequence name
    today = date.today()
    date_str = today.strftime('%Y%m%d')
    night_sequence["Name"] = date_str
    
    # Generate target containers for each target
    target_containers = []
    
    for i, target in enumerate(targets):
        target_name = target.get('name', 'Unknown')
        ra_str = target.get('ra', '00:00:00')
        dec_str = target.get('dec', '+00:00:00')
        is_last_target = (i == len(targets) - 1)
        
        # Parse RA (HH:MM:SS.SS format)
        ra_parts = ra_str.split(':')
        ra_hours = int(ra_parts[0]) if len(ra_parts) > 0 and ra_parts[0].strip() else 0
        ra_minutes = int(ra_parts[1]) if len(ra_parts) > 1 and ra_parts[1].strip() else 0
        ra_seconds = float(ra_parts[2]) if len(ra_parts) > 2 and ra_parts[2].strip() else 0.0
        
        # Parse Dec (±DD:MM:SS.SS format)
        dec_negative = dec_str.startswith('-')
        dec_str_abs = dec_str.lstrip('+-')
        dec_parts = dec_str_abs.split(':')
        dec_degrees = int(dec_parts[0]) if len(dec_parts) > 0 and dec_parts[0].strip() else 0
        if dec_negative:
            dec_degrees = -dec_degrees
        dec_minutes = int(dec_parts[1]) if len(dec_parts) > 1 and dec_parts[1].strip() else 0
        dec_seconds = float(dec_parts[2]) if len(dec_parts) > 2 and dec_parts[2].strip() else 0.0
        
        # Calculate exposure time (or use fixed 10s for S50)
        if telescope == "S50":
            if s50_exposure_override is not None:
                exposure_time = s50_exposure_override
                logger.info(f"Target {target_name}: Using custom S50 exposure time: {exposure_time}s")
            else:
                exposure_time = 10
                logger.info(f"Target {target_name}: Using default S50 exposure time: {exposure_time}s")
        else:
            mag_max_str = target.get('mag_max', '12.0')
            try:
                mag_max = float(mag_max_str)
                # Use instrument-specific exposure time scaling
                instrument = telescope if telescope in ['SCT', 'S50'] else 'SCT'
                exposure_time = get_exposure_time(mag_max, instrument=instrument)
            except (ValueError, TypeError):
                exposure_time = 40.0
                logger.warning(f"Could not parse magnitude for {target_name}, using default exposure time {exposure_time}s")
        
        # Create target container from template
        target_container = copy.deepcopy(target_template)
        
        # Update target name
        target_container["Target"]["TargetName"] = target_name
        target_container["Name"] = target_name
        
        # Update coordinates in all places
        update_coordinates(target_container, ra_hours, ra_minutes, ra_seconds, 
                         dec_negative, dec_degrees, dec_minutes, dec_seconds)
        
        # Update exposure time
        update_exposure_time(target_container, exposure_time)
        
        # Calculate observation time window
        minima_datetime = target.get('minima_datetime_local')
        if minima_datetime:
            start_time = minima_datetime - timedelta(hours=2)
            start_hours = start_time.hour
            start_minutes = start_time.minute
            
            if is_last_target:
                # For the last target, set end time to astronomical dawn
                obs_date = minima_datetime.date()
                dawn_time_str = calculate_astronomical_dawn(obs_date, LATITUDE, LONGITUDE)
                dawn_parts = dawn_time_str.split(':')
                end_hours = int(dawn_parts[0])
                end_minutes = int(dawn_parts[1])
            else:
                end_time = minima_datetime + timedelta(hours=2)
                end_hours = end_time.hour
                end_minutes = end_time.minute
        else:
            # Default to 20:00 if no time available
            start_hours = 20
            start_minutes = 0
            end_hours = 0 if not is_last_target else 6
            end_minutes = 0
        
        # Update end time condition
        update_end_time_condition(target_container, end_hours, end_minutes)
        
        # Update pushover message for last target
        if is_last_target:
            def update_pushover_message(obj, new_message):
                if isinstance(obj, dict):
                    if (obj.get("$type") == "DaleGhent.NINA.GroundStation.SendToPushover.SendToPushover, DaleGhent.NINA.GroundStation" and
                        obj.get("Title") == "$$TARGET_NAME$$ done"):
                        obj["Message"] = new_message
                    else:
                        for value in obj.values():
                            update_pushover_message(value, new_message)
                elif isinstance(obj, list):
                    for item in obj:
                        update_pushover_message(item, new_message)
            
            update_pushover_message(target_container, "done for the night")
        
        target_containers.append(target_container)
    
    # Fix Parent references for all target containers
    def fix_parent_references(containers, parent_ref="1"):
        """Fix Parent references to point to the sequence root"""
        for container in containers:
            # Set the target container's parent to the sequence root
            container["Parent"] = {"$ref": parent_ref}
            
            # Recursively fix all child Parent references
            def fix_child_parents(obj, container_id):
                if isinstance(obj, dict):
                    if "Parent" in obj and obj.get("$id") != container_id:
                        # Point it to the container
                        obj["Parent"] = {"$ref": container_id}
                    for value in obj.values():
                        if isinstance(value, (dict, list)):
                            fix_child_parents(value, container_id)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)):
                            fix_child_parents(item, container_id)
            
            # Fix all children to point to this container
            if container.get("$id"):
                fix_child_parents(container, container["$id"])
    
    fix_parent_references(target_containers)
    
    # Insert target containers into the night sequence
    # Find the TargetAreaContainer and insert targets there
    target_area_found = False
    for item in night_sequence["Items"]["$values"]:
        if item.get("$type") == "NINA.Sequencer.Container.TargetAreaContainer, NINA.Sequencer":
            # Found the target area container - replace its items with our targets
            item["Items"]["$values"] = target_containers
            target_area_found = True
            logger.info(f"Added {len(target_containers)} targets to TargetAreaContainer")
            break
    
    # If no TargetAreaContainer found, this is a problem with the template
    if not target_area_found:
        logger.error("No TargetAreaContainer found in night sequence template!")
        logger.error("Night sequence template must contain Start, Target, and End area containers")
        return None
    
    # Normalize all IDs to ensure uniqueness
    night_sequence = _normalize_nina_ids(night_sequence)
    
    # Save to file
    filename = f"{date_str}_night_sequence.json"
    filepath = output_dir / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(night_sequence, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created NINA night sequence file: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save night sequence file: {e}")
        return None


def check_already_observed(targets: List[Dict], observation_date: date, db_path: Path) -> tuple[List[str], List[str]]:
    """
    Check if any targets have already been observed or scheduled on the specified night.
    
    Args:
        targets: List of target dictionaries
        observation_date: Date to check for observations/scheduling
        db_path: Path to database
    
    Returns:
        Tuple of (already_observed_targets, already_scheduled_targets)
    """
    if not db_path.exists():
        return [], []
    
    obs_date_str = observation_date.strftime('%Y-%m-%d')
    already_observed = []
    already_scheduled = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for target in targets:
            target_name = target.get('name', target.get('Star', 'Unknown'))
            
            # Check if this target has exposures on this observation night
            cursor.execute('''

                SELECT COUNT(*) 
                FROM observations o
                JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id
                JOIN observation_nights on_ ON st.night_id = on_.night_id
                JOIN targets t ON st.target_id = t.target_id
                WHERE t.target_name = ? AND on_.date_obs = ?
            ''', (target_name, obs_date_str))
            
            count = cursor.fetchone()[0]
            if count > 0:
                already_observed.append(target_name)
            
            # Check if this target is already scheduled for this night (but not yet observed)
            # Exclude targets with status='failed' to allow rescheduling
            cursor.execute('''

                SELECT COUNT(*) 
                FROM scheduled_targets st
                JOIN observation_nights on_ ON st.night_id = on_.night_id
                JOIN targets t ON st.target_id = t.target_id
                WHERE t.target_name = ? AND on_.date_obs = ?
                AND (st.status IS NULL OR st.status != 'failed')
            ''', (target_name, obs_date_str))
            
            scheduled_count = cursor.fetchone()[0]
            if scheduled_count > 0 and target_name not in already_observed:
                already_scheduled.append(target_name)
        
        conn.close()
    except Exception as e:
        logger.warning(f"Could not check for already-observed/scheduled targets: {e}")
    
    return already_observed, already_scheduled


def prompt_user_confirmation(already_observed: List[str], already_scheduled: List[str], observation_date: date) -> bool:
    """
    Display a dialog box asking user if they want to proceed with scheduling
    targets that have already been observed or scheduled.
    
    Args:
        already_observed: List of target names already observed
        already_scheduled: List of target names already scheduled (but not observed)
        observation_date: Date targets are scheduled for
    
    Returns:
        True if user wants to proceed, False otherwise
    """
    # Create a hidden root window
    root = tk.Tk()
    root.withdraw()
    
    obs_date_str = observation_date.strftime('%Y-%m-%d')
    
    # Build message based on what was found
    message_parts = []
    
    if already_observed:
        if len(already_observed) == 1:
            message_parts.append(
                f"Target '{already_observed[0]}' has already been OBSERVED on {obs_date_str}."
            )
        else:
            targets_list = "\n  • ".join(already_observed)
            message_parts.append(
                f"The following {len(already_observed)} targets have already been OBSERVED on {obs_date_str}:\n"
                f"  • {targets_list}"
            )
    
    if already_scheduled:
        if len(already_scheduled) == 1:
            message_parts.append(
                f"Target '{already_scheduled[0]}' is already SCHEDULED for {obs_date_str} (not yet observed)."
            )
        else:
            targets_list = "\n  • ".join(already_scheduled)
            message_parts.append(
                f"The following {len(already_scheduled)} targets are already SCHEDULED for {obs_date_str} (not yet observed):\n"
                f"  • {targets_list}"
            )
    
    message = "\n\n".join(message_parts)
    message += "\n\nDo you want to schedule them again?"
    
    result = messagebox.askyesno(
        "Targets Already Observed or Scheduled",
        message,
        icon='warning'
    )
    
    root.destroy()
    return result


def record_scheduled_targets(targets: List[Dict], observation_date: date, db_path: Path = None, telescope: str = None):
    """
    Record scheduled targets in the observation database.
    
    Args:
        targets: List of target dictionaries with 'name', 'ra', 'dec', etc.
        observation_date: Date targets are scheduled for
        db_path: Path to database (optional, uses default if not specified)
        telescope: Telescope name (optional, defaults to 'SCT 8-inch')
    """
    if db_path is None:
        db_path = Path("Z:/scheduled_observations.sqlite")
        logger.info(f"Using database: {db_path}")

    if telescope is None:
        telescope = "SCT 8-inch"

    logger.info(f"record_scheduled_targets called with telescope='{telescope}' for {len(targets)} target(s)")

    # Check if any targets have already been observed or scheduled
    already_observed, already_scheduled = check_already_observed(targets, observation_date, db_path)

    if already_observed or already_scheduled:
        total_issues = len(already_observed) + len(already_scheduled)
        logger.warning(f"{total_issues} target(s) already observed or scheduled on {observation_date}")

        if not prompt_user_confirmation(already_observed, already_scheduled, observation_date):
            logger.info("User cancelled scheduling of already-observed/scheduled targets")
            return
        else:
            logger.info("User confirmed to proceed with scheduling")

    obs_date_str = observation_date.strftime('%Y-%m-%d')

    try:
        db = ObservationDB(str(db_path))
        night_id = db.add_night(obs_date_str, telescope=telescope)

        marked = 0
        for target in targets:
            target_name = target.get('name', target.get('Star', 'Unknown'))

            # Parse RA string (HH:MM:SS.SS) into components
            ra_str = target.get('ra', '') or ''
            ra_hours = ra_minutes = ra_seconds = None
            if ra_str.strip():
                ra_parts = ra_str.strip().split(':')
                try:
                    ra_hours   = int(ra_parts[0]) if len(ra_parts) > 0 and ra_parts[0].strip() else 0
                    ra_minutes = int(ra_parts[1]) if len(ra_parts) > 1 and ra_parts[1].strip() else 0
                    ra_seconds = float(ra_parts[2]) if len(ra_parts) > 2 and ra_parts[2].strip() else 0.0
                except (ValueError, IndexError):
                    ra_hours = ra_minutes = ra_seconds = None

            # Parse Dec string (±DD:MM:SS.SS) into components
            dec_str = target.get('dec', '') or ''
            dec_degrees = dec_minutes = dec_seconds = dec_negative = None
            if dec_str.strip():
                dec_negative = dec_str.strip().startswith('-')
                dec_str_abs = dec_str.strip().lstrip('+-')
                dec_parts = dec_str_abs.split(':')
                try:
                    dec_degrees = int(dec_parts[0]) if len(dec_parts) > 0 and dec_parts[0].strip() else 0
                    if dec_negative:
                        dec_degrees = -dec_degrees
                    dec_minutes = int(dec_parts[1]) if len(dec_parts) > 1 and dec_parts[1].strip() else 0
                    dec_seconds = float(dec_parts[2]) if len(dec_parts) > 2 and dec_parts[2].strip() else 0.0
                except (ValueError, IndexError):
                    dec_degrees = dec_minutes = dec_seconds = dec_negative = None

            # Upsert the target record
            target_id = db.add_target(
                target_name,
                target_type='variable_star',
                ra_hours=ra_hours,
                ra_minutes=ra_minutes,
                ra_seconds=ra_seconds,
                dec_degrees=dec_degrees,
                dec_minutes=dec_minutes,
                dec_seconds=dec_seconds,
                dec_negative=dec_negative,
                constellation=target.get('constellation') or None,
                magnitude_max=target.get('mag_max') or None,
                magnitude_min=target.get('mag_min') or None,
                variability_type=target.get('variability_type') or None,
            )

            # Resolve minima time to an ISO string if available
            minima_dt = target.get('minima_datetime_utc') or None
            if minima_dt is None:
                raw_min = target.get('minimum_time', '')
                if raw_min:
                    try:
                        minima_dt = parse_minima_time(raw_min)
                    except Exception:
                        minima_dt = None
            minima_iso = minima_dt.isoformat() if minima_dt else None

            start_dt = (minima_dt - timedelta(hours=2)) if minima_dt else None
            end_dt   = (minima_dt + timedelta(hours=2)) if minima_dt else None

            db.schedule_target(
                night_id=night_id,
                target_id=target_id,
                scheduled_start_time=start_dt.isoformat() if start_dt else None,
                scheduled_end_time=end_dt.isoformat() if end_dt else None,
                minima_time=minima_iso,
                observation_window_hours=OBSERVATION_WINDOW,
                status='scheduled',
            )
            marked += 1
            logger.info(f"Scheduled {target_name} for {obs_date_str}")

        logger.info(f"Created {marked} scheduled_targets record(s) in database for {obs_date_str}")
    except Exception as e:
        logger.error(f"Could not record scheduled targets in database: {e}")
        raise
    

if __name__ == "__main__":
    # Create targets output directory
    targets_dir = Path(__file__).parent / "targets"
    targets_dir.mkdir(exist_ok=True)
    
    # Fetch all targets (will use cache if available for today)
    targets = fetch_minima_predictions(max_pages=None, use_cache=True)
    
    if targets:
        # Export all filtered targets to targets directory
        all_targets_path = targets_dir / f"targets_{date.today()}.csv"
        export_to_nina_format(targets, all_targets_path)
        
        # Select optimal targets for tonight
        logger.info("Selecting optimal targets for tonight...")
        selected = select_targets_for_night(targets)
        
        if selected:
            # Export selected targets to targets directory
            selected_path = targets_dir / f"selected_targets_{date.today()}.csv"
            export_to_nina_format(selected, selected_path)
            logger.info(f"Exported {len(selected)} selected targets for tonight")
            
            # Export NINA JSON files to targets directory
            export_to_nina_json(selected, output_dir=targets_dir)
            
            logger.info("Note: Targets are not recorded in database when using command-line interface.")
            logger.info("Use the GUI to record targets in the database upon export.")
        else:
            logger.warning("No suitable targets found for tonight")
