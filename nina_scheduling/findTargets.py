# using a calll to https://var.astro.cz/en/Stars/MinimaPredictions?pageId=1&pageSize=20&obsLat=50&obsLong=15&tabId=predTab1&date=2025-10-25&showVisibleEventsOnly=true
# with the users latitude and longitude set to -35 and 150 respectively
# we collect the minima predictions for the next night 
# from this list we draw targets for nina scheduling

import logging
import re
from datetime import date
from pathlib import Path
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from secrets import VARASTRO_USERNAME, VARASTRO_PASSWORD
from datetime import datetime, timedelta
import math

# Astropy imports for accurate astronomical calculations
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, SkyCoord as coord
from astropy.time import Time
import astropy.units as u
from astroquery.simbad import Simbad

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User configuration
LATITUDE = -35
LONGITUDE = 150
BASE_URL = "https://var.astro.cz/en/Stars/MinimaPredictions"
USERNAME = VARASTRO_USERNAME
PASSWORD = VARASTRO_PASSWORD
MAG_MIN = 10
MAG_MAX = 12.5  # Expanded back to original range
MIN_ALTITUDE = 45  # Minimum elevation at minima in degrees
ALLOWED_AZIMUTHS = ['N', 'NE', 'NW', 'E', 'W']  # Allowed azimuth directions

# Observation scheduling parameters
OBSERVATION_WINDOW = 4  # Hours: 2 hours before + 2 hours after minima
MIN_ALTITUDE_DURING_OBS = 30  # Minimum altitude during observation window
TARGET_SPACING = 4  # Hours between target minima
SUNSET_TIME = "20:00"  # Default sunset time LOCAL TIME
MAX_TARGETS_PER_NIGHT = 2  # Usually only 2 targets fit per night
TIMEZONE_OFFSET = 10  # Hours ahead of UTC (UTC+10 for longitude 150°E)

def login_to_portal(session: requests.Session) -> bool:
    """
    Login to var.astro.cz portal
    
    Args:
        session: requests Session object
        
    Returns:
        True if login successful, False otherwise
    """
    login_url = "https://var.astro.cz/en/Identity/Account/Login"
    
    try:
        # Get login page to retrieve CSRF token
        logger.info("Fetching login page to get CSRF token...")
        response = session.get(login_url)
        
        # Save login page for debugging
        debug_path = Path(__file__).parent / "login_page.html"
        debug_path.write_text(response.text)
        logger.info(f"Login page saved to {debug_path}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the login form (it doesn't have an action attribute, so just find any form)
        login_form = soup.find('form')
        if not login_form:
            logger.error("Could not find login form")
            return False
        
        logger.info("Login form found")
        
        # Extract all hidden fields from the form
        login_data = {}
        for hidden_input in login_form.find_all('input', {'type': 'hidden'}):
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name:
                login_data[name] = value
                logger.info(f"Found hidden field: {name} = {value[:20]}...")
        
        # Add username and password
        login_data['Input.Email'] = USERNAME
        login_data['Input.Password'] = PASSWORD
        login_data['Input.RememberMe'] = 'false'
        
        # Post login credentials
        logger.info("Attempting login...")
        response = session.post(login_url, data=login_data, allow_redirects=True)
        
        # Save debug info
        debug_path = Path(__file__).parent / "login_response.html"
        debug_path.write_text(response.text)
        logger.info(f"Login response saved to {debug_path}")
        
        # Check if we're logged in by looking for user-specific content
        if 'logout' in response.text.lower() or 'log out' in response.text.lower():
            logger.info("Login successful")
            return True
        else:
            logger.error("Login may have failed - no logout link found")
            # Check for error messages
            soup = BeautifulSoup(response.text, 'html.parser')
            error_div = soup.find('div', class_=['alert-danger', 'validation-summary-errors'])
            if error_div:
                logger.error(f"Login error message: {error_div.get_text().strip()}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Login error: {e}")
        return False
        
        # Post login credentials
        logger.info("Attempting login...")
        response = session.post(login_url, data=login_data, allow_redirects=True)
        
        # Check if login was successful by looking for error messages or redirect
        if 'login' not in response.url.lower() or response.status_code == 200:
            # Save debug info
            debug_path = Path(__file__).parent / "login_response.html"
            debug_path.write_text(response.text)
            logger.info(f"Login response saved to {debug_path}")
            
            # Check if we're logged in by looking for user-specific content
            if 'logout' in response.text.lower() or 'log out' in response.text.lower():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login may have failed - no logout link found")
                return False
        else:
            logger.error(f"Login failed - redirected back to login page")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Login error: {e}")
        return False

def fetch_minima_predictions(obs_date: date = None, page_size: int = 100, max_pages: int = None, use_cache: bool = True) -> List[Dict]:
    """
    Fetch minima predictions from var.astro.cz using Selenium
    
    Args:
        obs_date: Observation date (defaults to today)
        page_size: Number of results to fetch (will handle pagination)
        max_pages: Maximum number of pages to fetch (None = all pages, useful for testing)
        use_cache: If True, use cached data if available for the same date
        
    Returns:
        List of target dictionaries
    """
    if obs_date is None:
        obs_date = date.today()
    
    # Check for cached data
    cache_file = Path(__file__).parent / f"cache_raw_targets_{obs_date}.json"
    if use_cache and cache_file.exists():
        logger.info(f"Found cached data for {obs_date}, loading from {cache_file}")
        with open(cache_file, 'r', encoding='utf-8') as f:
            targets = json.load(f)
        logger.info(f"Loaded {len(targets)} targets from cache")
        
        # Apply filters to cached data
        filtered_targets = apply_filters(targets)
        logger.info(f"After applying filters: {len(filtered_targets)} targets remain")
        return filtered_targets
    
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
        pred_url = (f"https://var.astro.cz/en/Stars/MinimaPredictions?init=1"
                   f"&obsLat={LATITUDE}&obsLong={LONGITUDE}"
                   f"&date={obs_date.strftime('%Y-%m-%d')}"
                   f"&showVisibleEventsOnly=true")
        driver.get(pred_url)
        logger.info(f"Loading predictions page for {obs_date}...")
        
        # Wait for page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "minima-pred-table"))
        )
        
        # Fill in filter fields directly
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
            
            logger.info(f"Applied filters: mag {MAG_MIN}-{MAG_MAX}, alt >{MIN_ALTITUDE}°, azimuth={azimuth_filter}")
            
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
                    target = {
                        'id': cells[0].text.strip(),
                        'entries': cells[1].text.strip(),
                        'name': cells[2].text.strip(),
                        'constellation': cells[3].text.strip(),
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
        
        # Save raw data to cache
        cache_file = Path(__file__).parent / f"cache_raw_targets_{obs_date}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(targets, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved raw data to cache: {cache_file}")
        
        # Apply post-processing filters
        filtered_targets = apply_filters(targets)
        logger.info(f"After applying filters: {len(filtered_targets)} targets remain")
        
        return filtered_targets
        
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

def apply_filters(targets: List[Dict]) -> List[Dict]:
    """
    Apply filters to the targets list
    
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
        'passed': 0
    }
    
    for target in targets:
        passed = True
        
        # Filter by magnitude
        try:
            mag_max = float(target.get('mag_max', '0').replace(',', '.'))
            mag_min = float(target.get('mag_min', '0').replace(',', '.'))
            
            if not (MAG_MIN <= mag_max <= MAG_MAX or MAG_MIN <= mag_min <= MAG_MAX):
                stats['magnitude_filtered'] += 1
                passed = False
                continue
        except (ValueError, AttributeError):
            passed = False
            continue
        
        # Filter by altitude
        try:
            altitude = float(target.get('altitude', '0').replace(',', '.').replace('°', ''))
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
            stats['passed'] += 1
            
            # Try to get RA/Dec if not already present
            if not target.get('ra') or not target.get('dec'):
                star_name = target.get('name', '')
                constellation = target.get('constellation', '')
                
                # Only lookup coordinates for a subset to avoid too many queries
                # We'll lookup as needed during altitude checking
                target['ra'] = ''
                target['dec'] = ''
            
            filtered.append(target)
    
    logger.info(f"Filter stats: {stats['passed']} passed, "
                f"{stats['magnitude_filtered']} filtered by magnitude, "
                f"{stats['altitude_filtered']} filtered by altitude, "
                f"{stats['azimuth_filtered']} filtered by azimuth")
    
    return filtered

    return filtered

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
        star_name: Star name (e.g., "V1812", "KQ")
        constellation: Constellation abbreviation (e.g., "Aql", "Psc")
        
    Returns:
        Tuple of (ra_str, dec_str) or (None, None) if not found
    """
    try:
        # SIMBAD requires full name with constellation
        if not constellation:
            logger.debug(f"No constellation provided for {star_name}, cannot query SIMBAD")
            return (None, None)
        
        query_name = f"{star_name} {constellation}"
        
        # Query SIMBAD
        result_table = Simbad.query_object(query_name)
        
        if result_table is not None and len(result_table) > 0:
            # Get RA/Dec from result
            ra = result_table['RA'][0]  # Format: "HH MM SS.ss"
            dec = result_table['DEC'][0]  # Format: "+DD MM SS.s"
            
            # Convert to standard format
            ra_str = ra.replace(' ', ':')
            dec_str = dec.replace(' ', ':')
            
            logger.debug(f"Found coordinates for {query_name}: RA={ra_str}, Dec={dec_str}")
            return (ra_str, dec_str)
            
        return (None, None)
        
    except Exception as e:
        logger.debug(f"Could not lookup coordinates for {star_name} {constellation}: {e}")
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

def check_altitude_during_observation(target: Dict, lat: float, lon: float) -> bool:
    """
    Check if target maintains sufficient altitude throughout observation window
    
    Uses astropy to calculate actual altitude at multiple points during the
    4-hour observation window (2 hours before to 2 hours after minima).
    
    Args:
        target: Target dictionary with minima time and RA/Dec coordinates
        lat: Observer latitude in degrees
        lon: Observer longitude in degrees
        
    Returns:
        True if target maintains >30° altitude throughout observation window
    """
    try:
        # Get RA/Dec coordinates
        ra = target.get('ra', '')
        dec = target.get('dec', '')
        
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

def select_targets_for_night(targets: List[Dict], dark_sky_time: str = None) -> List[Dict]:
    """
    Select optimal targets for the night based on timing and altitude constraints
    
    Args:
        targets: List of filtered target dictionaries
        dark_sky_time: Dark sky start time as "HH:MM" string in LOCAL TIME (if None, will calculate for sun at -15°)
        
    Returns:
        List of selected targets for the night (usually 2)
    """
    # Calculate or parse dark sky time (local)
    today = date.today()
    
    if dark_sky_time is None:
        # Calculate when sun reaches -15° below horizon (dark enough for observations)
        dark_sky_time = calculate_sunset_time(today, LATITUDE, LONGITUDE, sun_altitude=-15.0)
        logger.info(f"Calculated dark sky time (sun at -15°): {dark_sky_time} local")
    
    dark_sky_local = datetime.combine(today, datetime.strptime(dark_sky_time, "%H:%M").time())
    
    # First target should have minima ~2 hours after dark sky begins (local time)
    # This ensures observations can start right at dark sky time (2hrs before minima)
    first_target_local = dark_sky_local + timedelta(hours=2)
    # Convert to UTC for comparison with target times
    first_target_utc = local_to_utc(first_target_local)
    
    logger.info(f"Dark sky begins at {dark_sky_local.strftime('%H:%M')} local")
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
                logger.debug(f"Skipping {target['name']} ({target.get('constellation', '')}) - observation would start at {obs_start_time_only} before dark sky at {dark_sky_time_only}")
    
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
            # Check altitude during observation window
            if check_altitude_during_observation(target, LATITUDE, LONGITUDE):
                first_target_candidates.append((target, hour_diff))
    
    # Sort by time difference and pick the closest
    if first_target_candidates:
        first_target_candidates.sort(key=lambda x: x[1])
        best_first_target = first_target_candidates[0][0]
        selected_targets.append(best_first_target)
        logger.info(f"Selected target 1: {best_first_target['name']} ({best_first_target.get('constellation', '')}) at {best_first_target['minima_datetime_local'].strftime('%H:%M')} local ({best_first_target['minimum_time']} UTC)")
        
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
                if check_altitude_during_observation(target, LATITUDE, LONGITUDE):
                    second_target_candidates.append((target, time_diff))
        
        # Sort by time difference and pick the closest
        if second_target_candidates:
            second_target_candidates.sort(key=lambda x: x[1])
            best_second_target = second_target_candidates[0][0]
            selected_targets.append(best_second_target)
            logger.info(f"Selected target 2: {best_second_target['name']} ({best_second_target.get('constellation', '')}) at {best_second_target['minima_datetime_local'].strftime('%H:%M')} local ({best_second_target['minimum_time']} UTC)")
    
    return selected_targets[:MAX_TARGETS_PER_NIGHT]

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
    
if __name__ == "__main__":
    # Fetch all targets (will use cache if available for today)
    targets = fetch_minima_predictions(max_pages=None, use_cache=True)
    
    if targets:
        # Export all filtered targets
        export_to_nina_format(targets)
        
        # Select optimal targets for tonight
        logger.info("Selecting optimal targets for tonight...")
        selected = select_targets_for_night(targets)
        
        if selected:
            # Export selected targets
            selected_path = Path(__file__).parent / f"selected_targets_{date.today()}.csv"
            export_to_nina_format(selected, selected_path)
            logger.info(f"Exported {len(selected)} selected targets for tonight")
        else:
            logger.warning("No suitable targets found for tonight")
