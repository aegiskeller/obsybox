#!/usr/bin/env python3
"""
Scan D:/ for SCT and S50 observation directories and populate scheduled_observations.sqlite

Modes:
 - light: scan immediate children of --base-path for LIGHT subdirectory
 - seestar: scan --seestar-path for yyyymmdd folders
 - both: run both scans

Populates the existing schema:
 - targets table
 - observation_nights table
 - scheduled_targets table (links targets to nights)
"""
from pathlib import Path
import argparse
import logging
import re
import sqlite3
from datetime import date, datetime
import sys

try:
    from astropy.io import fits
    HAVE_ASTROPY = True
except ImportError:
    HAVE_ASTROPY = False
    logging.warning("astropy not available - FITS header reading disabled")

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def read_fits_header(fits_path: Path):
    """Read FITS header and extract key metadata.
    Returns dict with: filter, exptime, binning, gain, offset, temp, datetime
    """
    if not HAVE_ASTROPY:
        return {}
    
    try:
        with fits.open(str(fits_path), ignore_missing_simple=True, memmap=True) as hdul:
            if len(hdul) == 0:
                return {}
            
            header = hdul[0].header
            
            # Common FITS keywords (NINA, MaxIm, etc.)
            result = {
                'filter': header.get('FILTER', header.get('FILTNAM', None)),
                'exptime': header.get('EXPTIME', header.get('EXPOSURE', None)),
                'binning': header.get('XBINNING', None),
                'gain': header.get('GAIN', None),
                'offset': header.get('OFFSET', None),
                'temp': header.get('CCD-TEMP', header.get('SET-TEMP', None)),
                'datetime': header.get('DATE-OBS', None),
                'imagetyp': header.get('IMAGETYP', header.get('FRAME', None)),
            }
            
            # Construct binning string if available
            if result['binning']:
                ybinning = header.get('YBINNING', result['binning'])
                result['binning'] = f"{result['binning']}x{ybinning}"
            
            return result
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logging.debug(f"Failed to read FITS header from {fits_path.name}: {e}")
        return {}


def parse_filename_metadata(filename: str):
    """Extract metadata from NINA-style filenames.
    Format: YYYY-MM-DD_HH-MM-SS_FILTER_TEMP_EXPTIMEs_NNNN.fits
    Example: 2024-02-01_20-42-53_R_-10.00_6.31s_0000.fits
    Returns dict with filter, exptime, temp
    """
    result = {}
    
    # Try to extract filter, temp, and exposure time from filename
    # Pattern: ..._FILTER_TEMP_TIMEs_...
    pattern = r'_([A-Za-z]+)_(-?\d+\.?\d*)_(\d+\.?\d*)s_'
    match = re.search(pattern, filename)
    if match:
        result['filter'] = match.group(1)
        result['temp'] = float(match.group(2))
        result['exptime'] = float(match.group(3))
    else:
        # Try simpler pattern for just filter
        filter_pattern = r'_([LRGBVIHSO][a-z]*)_'
        filter_match = re.search(filter_pattern, filename)
        if filter_match:
            result['filter'] = filter_match.group(1)
    
    return result


def scan_fits_files(directory: Path, read_headers: bool = True, frame_type: str = 'LIGHT', verbose: bool = False):
    """Scan directory for FITS files and return list of file info dicts.
    Each dict contains: file_path, filter, exptime, binning, etc.
    
    Args:
        directory: Path to scan
        read_headers: If True, read FITS headers. If False, only parse filenames (faster)
        frame_type: Type of frame (LIGHT, FLAT, BIAS, DARK) for logging
        verbose: If True, log each file as it's processed
    """
    if not directory.exists() or not directory.is_dir():
        return []
    
    results = []
    fits_extensions = ['.fits', '.fit', '.fts', '.xisf']
    
    try:
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in fits_extensions:
                header_info = {}
                
                if read_headers:
                    if verbose or frame_type in ['FLAT', 'BIAS', 'DARK']:
                        logging.info(f"Reading {frame_type}: {file_path.name}")
                    try:
                        header_info = read_fits_header(file_path)
                        if verbose and header_info:
                            logging.info(f"  → filter={header_info.get('filter')}, exp={header_info.get('exptime')}s, temp={header_info.get('temp')}°C")
                    except KeyboardInterrupt:
                        raise
                    except Exception as e:
                        logging.warning(f"Error reading {file_path.name}: {e}")
                        header_info = {}
                
                # If FITS header reading failed or disabled, try to parse filename
                if not header_info or not header_info.get('filter'):
                    filename_info = parse_filename_metadata(file_path.name)
                    # Merge filename info with header info (header takes precedence)
                    for key, value in filename_info.items():
                        if key not in header_info or header_info[key] is None:
                            header_info[key] = value
                    if verbose and filename_info:
                        logging.info(f"  → (from filename) filter={filename_info.get('filter')}, exp={filename_info.get('exptime')}s, temp={filename_info.get('temp')}°C")
                
                results.append({
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'file_size': file_path.stat().st_size,
                    **header_info
                })
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logging.warning(f"Failed to scan FITS files in {directory}: {e}")
    
    return results


def parse_args():
    p = argparse.ArgumentParser(description='Scan for LIGHT and Seestar data dirs and populate observation DB')
    p.add_argument('--mode', choices=('light', 'seestar', 'both'), default='both', help='Which scans to run')
    p.add_argument('--base-path', default='D:\\', help='Base path to scan for LIGHT (default D:\\)')
    p.add_argument('--seestar-path', default='D:\\Seestar', help='Path to scan for Seestar date folders (default D:\\Seestar)')
    p.add_argument('--date-dir', help='Scan a specific date directory directly (e.g., D:\\2024\\2024-02-01)')
    p.add_argument('--db', default='D:\\scheduled_observations.sqlite', help='SQLite DB path')
    p.add_argument('--dry-run', action='store_true', help='Do not write to DB; show actions')
    p.add_argument('--verbose', action='store_true')
    p.add_argument('--strip-sub-suffix', action='store_true', default=True,
                   help='Strip trailing _sub and any following suffixes (e.g., _sub_d -> remove)')
    return p.parse_args()


def parse_date_dirname(name: str):
    """Parse directory name as date. Returns yyyy-mm-dd string or None.
    Supports: YYYY-MM-DD, YYYYMMDD, YYYY (assumes Jan 1)
    """
    # YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', name):
        try:
            _ = date.fromisoformat(name)
            return name
        except Exception:
            return None
    
    # YYYYMMDD format
    if re.match(r'^\d{8}$', name):
        try:
            yyyy = name[0:4]
            mm = name[4:6]
            dd = name[6:8]
            iso = f"{yyyy}-{mm}-{dd}"
            _ = date.fromisoformat(iso)
            return iso
        except Exception:
            return None
    
    # YYYY format (assume Jan 1)
    if re.match(r'^\d{4}$', name):
        try:
            yyyy = name
            iso = f"{yyyy}-01-01"
            _ = date.fromisoformat(iso)
            return iso
        except Exception:
            return None
    
    return None


def find_light_subdirs_recursive(path: Path, strip_sub_suffix: bool = True, results=None, depth=0, max_depth=5):
    """Recursively scan for date-named directories containing frame type folders.
    Scans FITS files in LIGHT, FLAT, BIAS, DARK directories.
    Returns list of dicts: {target, dateobs, telescope, frame_type, filter, file_path, file_name, exptime, binning, ...}
    """
    if results is None:
        results = []
    
    if depth > max_depth:
        return results
    
    if not path.exists() or not path.is_dir():
        return results
    
    # Frame types to scan for
    frame_types = ['LIGHT', 'FLAT', 'BIAS', 'DARK']
    
    try:
        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            
            # Parse date from directory name
            dateobs = parse_date_dirname(child.name)
            
            # Scan each frame type directory
            for frame_type in frame_types:
                frame_dir = child / frame_type
                if not frame_dir.exists():
                    # Try lowercase
                    alt = child / frame_type.lower()
                    if alt.exists() and alt.is_dir():
                        frame_dir = alt
                    else:
                        continue
                
                if not frame_dir.is_dir():
                    continue
                
                try:
                    # Scan subdirectories within frame type folder
                    for subdir in sorted(frame_dir.iterdir()):
                        if subdir.is_dir():
                            # Scan FITS files in this subdirectory
                            # Always read headers to populate database properly
                            fits_files = scan_fits_files(subdir, read_headers=True, frame_type=frame_type)
                            
                            for fits_info in fits_files:
                                target_name = subdir.name
                                
                                if frame_type == 'LIGHT':
                                    # For LIGHT frames, directory name is the target
                                    if strip_sub_suffix:
                                        target_name = re.sub(r'(_sub)(?:_.*)?$', '', target_name, flags=re.IGNORECASE)
                                elif frame_type == 'FLAT':
                                    # For FLAT frames, use filter from FITS header or directory name
                                    filter_name = fits_info.get('filter') or subdir.name
                                    target_name = f'FLAT_{filter_name}'
                                elif frame_type == 'BIAS':
                                    target_name = 'BIAS'
                                elif frame_type == 'DARK':
                                    # Include exposure time in dark name if available
                                    exp = fits_info.get('exptime')
                                    if exp:
                                        target_name = f'DARK_{int(exp)}s'
                                    else:
                                        target_name = f'DARK_{subdir.name}'
                                
                                results.append({
                                    'target': target_name,
                                    'dateobs': dateobs,
                                    'telescope': 'SCT',
                                    'frame_type': frame_type,
                                    'source_path': str(subdir),
                                    **fits_info
                                })
                except Exception as e:
                    logging.warning('Failed listing %s dir %s: %s', frame_type, frame_dir, e)
            
            # Check if this is a date-formatted directory - recurse into it
            if dateobs:
                find_light_subdirs_recursive(child, strip_sub_suffix, results, depth + 1, max_depth)
    
    except Exception as e:
        logging.warning('Failed scanning %s: %s', path, e)
    
    return results


def find_light_subdirs(base_path: Path, strip_sub_suffix: bool = True):
    """Scan base_path recursively for date-named directories with LIGHT folders.
    Returns list of dicts: {target, dateobs, telescope, source_path}
    """
    results = []
    if not base_path.exists() or not base_path.is_dir():
        logging.warning('Base path %s missing or not a dir', base_path)
        return results
    
    return find_light_subdirs_recursive(base_path, strip_sub_suffix)


def clean_target_name(name: str) -> str:
    """Clean up target name by removing quotes and adding spaces after uppercase letters."""
    # Remove leading/trailing quotes (single or double)
    name = name.strip("'\"")
    
    # Add space between uppercase letter pairs (e.g., AACet -> AA Cet)
    # Only if we have a pattern like XXYyy where XX are uppercase and Yyy starts with uppercase
    name = re.sub(r'([A-Z]{2})([A-Z][a-z])', r'\1 \2', name)
    
    return name


def scan_seestar_recursive(path: Path, strip_sub_suffix: bool = True, results=None, depth=0, max_depth=5):
    """Recursively scan for date-named directories containing target subdirectories.
    Also looks inside LIGHT, FLAT, BIAS, DARK subdirectories for frames.
    Scans FITS files and extracts header information.
    Returns list of dicts: {target, dateobs, telescope, frame_type, filter, file_path, ...}
    """
    if results is None:
        results = []
    
    if depth > max_depth:
        return results
    
    if not path.exists() or not path.is_dir():
        return results
    
    # Frame types to scan for
    frame_types = ['LIGHT', 'FLAT', 'BIAS', 'DARK']
    
    try:
        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            
            # Try to parse this directory name as a date
            dateobs = parse_date_dirname(child.name)
            
            if dateobs:
                # This is a date directory - check for frame type subfolders
                found_frame_dir = False
                
                for frame_type in frame_types:
                    frame_dir = child / frame_type
                    if not frame_dir.exists():
                        alt = child / frame_type.lower()
                        if alt.exists() and alt.is_dir():
                            frame_dir = alt
                        else:
                            continue
                    
                    if frame_dir.is_dir():
                        found_frame_dir = True
                        # Found a frame type directory - scan its subdirectories
                        try:
                            for subdir in sorted(frame_dir.iterdir()):
                                if subdir.is_dir():
                                    # Scan FITS files in this subdirectory
                                    # Always read headers to populate database properly
                                    fits_files = scan_fits_files(subdir, read_headers=True, frame_type=frame_type)
                                    
                                    for fits_info in fits_files:
                                        target_name = subdir.name
                                        
                                        if frame_type == 'LIGHT':
                                            # For LIGHT frames, directory name is the target
                                            if strip_sub_suffix:
                                                target_name = re.sub(r'(_sub)(?:_.*)?$', '', target_name, flags=re.IGNORECASE)
                                                target_name = re.sub(r'(-sub)(?:_.*)?$', '', target_name, flags=re.IGNORECASE)
                                            target_name = clean_target_name(target_name)
                                        elif frame_type == 'FLAT':
                                            # For FLAT frames, use filter from FITS header or directory name
                                            filter_name = fits_info.get('filter') or subdir.name
                                            target_name = f'FLAT_{filter_name}'
                                        elif frame_type == 'BIAS':
                                            target_name = 'BIAS'
                                        elif frame_type == 'DARK':
                                            # Include exposure time in dark name if available
                                            exp = fits_info.get('exptime')
                                            if exp:
                                                target_name = f'DARK_{int(exp)}s'
                                            else:
                                                target_name = f'DARK_{subdir.name}'
                                        
                                        results.append({
                                            'target': target_name,
                                            'dateobs': dateobs,
                                            'telescope': 'S50',
                                            'frame_type': frame_type,
                                            'source_path': str(subdir),
                                            **fits_info
                                        })
                        except Exception as e:
                            logging.warning('Failed listing Seestar %s dir %s: %s', frame_type, frame_dir, e)
                
                # If no frame directories found, scan immediate subdirectories as LIGHT targets
                if not found_frame_dir:
                    try:
                        for subdir in sorted(child.iterdir()):
                            if not subdir.is_dir():
                                continue
                            
                            # Scan FITS files in this subdirectory
                            fits_files = scan_fits_files(subdir, read_headers=True, frame_type='LIGHT')
                            
                            for fits_info in fits_files:
                                target_name = subdir.name
                                if strip_sub_suffix:
                                    target_name = re.sub(r'(_sub)(?:_.*)?$', '', target_name, flags=re.IGNORECASE)
                                    target_name = re.sub(r'(-sub)(?:_.*)?$', '', target_name, flags=re.IGNORECASE)
                                target_name = clean_target_name(target_name)
                                
                                results.append({
                                    'target': target_name,
                                    'dateobs': dateobs,
                                    'telescope': 'S50',
                                    'frame_type': 'LIGHT',
                                    'source_path': str(subdir),
                                    **fits_info
                                })
                    except Exception as e:
                        logging.warning('Failed listing Seestar date dir %s: %s', child, e)
                
                # Also recurse into date directories (for nested date structures)
                scan_seestar_recursive(child, strip_sub_suffix, results, depth + 1, max_depth)
    
    except Exception as e:
        logging.warning('Failed scanning %s: %s', path, e)
    
    return results


def scan_seestar(seestar_path: Path, strip_sub_suffix: bool = True):
    """Scan Seestar path recursively for date-formatted directories.
    Returns list of dicts: {target, dateobs, telescope, source_path}
    """
    results = []
    if not seestar_path.exists() or not seestar_path.is_dir():
        logging.warning('Seestar path %s missing or not a dir', seestar_path)
        return results
    
    return scan_seestar_recursive(seestar_path, strip_sub_suffix)


def get_or_create_target(cur, target_name):
    """Get target_id or create new target entry. Returns target_id."""
    cur.execute('SELECT target_id FROM targets WHERE target_name = ?', (target_name,))
    row = cur.fetchone()
    if row:
        return row[0]
    
    # Create new target
    cur.execute('''
        INSERT INTO targets (target_name, target_type, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    ''', (target_name, 'variable_star', datetime.utcnow(), datetime.utcnow()))
    return cur.lastrowid


def get_or_create_night(cur, dateobs, telescope):
    """Get night_id or create new observation_nights entry. Returns night_id."""
    cur.execute('SELECT night_id FROM observation_nights WHERE date_obs = ?', (dateobs,))
    row = cur.fetchone()
    if row:
        return row[0]
    
    # Create new night
    cur.execute('''
        INSERT INTO observation_nights (date_obs, telescope, created_at)
        VALUES (?, ?, ?)
    ''', (dateobs, telescope, datetime.utcnow()))
    return cur.lastrowid


def insert_scheduled_target(cur, night_id, target_id, telescope, source_path, dry_run=False):
    """Insert or skip scheduled_target entry. Returns True if inserted."""
    # Check if already exists
    cur.execute('''
        SELECT scheduled_target_id FROM scheduled_targets 
        WHERE night_id = ? AND target_id = ?
    ''', (night_id, target_id))
    if cur.fetchone():
        return False
    
    if dry_run:
        return True
    
    # Insert new scheduled_target
    cur.execute('''
        INSERT INTO scheduled_targets (
            night_id, target_id, status, created_at
        ) VALUES (?, ?, ?, ?)
    ''', (night_id, target_id, 'completed', datetime.utcnow()))
    return True


def process_rows(rows, db_path: Path, dry_run: bool = False):
    """Process scan results and populate database."""
    if not rows:
        logging.info('No rows to process')
        return 0
    
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    # Separate calibration frames from light frames
    calibration_rows = []
    light_rows = []
    
    for r in rows:
        frame_type = r.get('frame_type', 'LIGHT')
        if frame_type in ['FLAT', 'BIAS', 'DARK']:
            calibration_rows.append(r)
        else:
            light_rows.append(r)
    
    if dry_run:
        logging.info(f"\n{'='*100}\nPROCESSING CALIBRATION FRAMES - {len(calibration_rows)} files\n{'='*100}\n")
        
        # Show each calibration frame insert
        for i, r in enumerate(calibration_rows, 1):
            frame_type = r.get('frame_type', 'UNKNOWN').lower()
            file_path = r.get('file_path')
            file_name = r.get('file_name')
            exptime = r.get('exptime')
            temp = r.get('temp')
            binning = r.get('binning')
            filter_name = r.get('filter')
            gain = r.get('gain')
            offset = r.get('offset')
            dateobs = r.get('dateobs')
            
            print(f"\n[{i}/{len(calibration_rows)}] {frame_type.upper()}: {file_name}")
            print(f"  INSERT INTO calibration_frames (")
            print(f"    frame_type, file_path, exposure_time_sec, temperature_c,")
            print(f"    binning, filter_name, gain, offset, date_created")
            print(f"  ) VALUES (")
            print(f"    '{frame_type}', '{file_path}',")
            print(f"    {exptime if exptime else 'NULL'}, {temp if temp else 'NULL'},")
            print(f"    {repr(binning) if binning else 'NULL'}, {repr(filter_name) if filter_name else 'NULL'},")
            print(f"    {gain if gain else 'NULL'}, {offset if offset else 'NULL'}, '{dateobs}'")
            print(f"  );")
        
        # Light frame individual inserts
        logging.info(f"\n{'='*100}\nPROCESSING LIGHT FRAMES - {len(light_rows)} files\n{'='*100}\n")
        
        for i, r in enumerate(light_rows, 1):
            target = r.get('target')
            dateobs = r.get('dateobs') or date.today().isoformat()
            telescope = r.get('telescope')
            file_path = r.get('file_path')
            file_name = r.get('file_name')
            exptime = r.get('exptime')
            temp = r.get('temp')
            binning = r.get('binning')
            filter_name = r.get('filter')
            gain = r.get('gain')
            offset = r.get('offset')
            
            print(f"\n[{i}/{len(light_rows)}] LIGHT: {file_name}")
            print(f"  -- Target: {target}, Date: {dateobs}, Telescope: {telescope}")
            print(f"  -- Would ensure target_id exists for '{target}'")
            print(f"  -- Would ensure night_id exists for date '{dateobs}', telescope '{telescope}'")
            print(f"  -- Would link target to night in scheduled_targets table")
            print(f"  INSERT INTO observations (")
            print(f"    file_path, exposure_time_sec, temperature_c, binning,")
            print(f"    filter_name, gain, offset, observation_datetime")
            print(f"  ) VALUES (")
            print(f"    '{file_path}',")
            print(f"    {exptime if exptime else 'NULL'}, {temp if temp else 'NULL'},")
            print(f"    {repr(binning) if binning else 'NULL'}, {repr(filter_name) if filter_name else 'NULL'},")
            print(f"    {gain if gain else 'NULL'}, {offset if offset else 'NULL'},")
            print(f"    {repr(r.get('datetime')) if r.get('datetime') else 'NULL'}")
            print(f"  );")
        
        logging.info(f"\n{'='*100}")
        logging.info(f"SUMMARY: {len(calibration_rows)} calibration frames, {len(light_rows)} light frames")
        logging.info(f"Total files: {len(rows)}")
        logging.info(f"{'='*100}\n")
        
        return len(calibration_rows)
    
    # Actual database insertion
    logging.info(f'Inserting {len(calibration_rows)} calibration frames and {len(light_rows)} light frames into database...')
    
    # Insert calibration frames
    for i, r in enumerate(calibration_rows, 1):
        frame_type = r.get('frame_type', 'UNKNOWN').lower()
        file_path = r.get('file_path')
        
        # Check if already exists
        cur.execute('SELECT calibration_id FROM calibration_frames WHERE file_path = ?', (file_path,))
        if cur.fetchone():
            skipped += 1
            continue
        
        try:
            cur.execute('''
                INSERT INTO calibration_frames (
                    frame_type, file_path, exposure_time_sec, temperature_c,
                    binning, filter_name, gain, offset, date_created
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                frame_type,
                file_path,
                r.get('exptime'),
                r.get('temp'),
                r.get('binning'),
                r.get('filter'),
                r.get('gain'),
                r.get('offset'),
                r.get('dateobs')
            ))
            inserted += 1
            if i % 100 == 0:
                logging.info(f'Inserted {i}/{len(calibration_rows)} calibration frames...')
                conn.commit()  # Commit every 100 frames so progress is visible
        except Exception as e:
            logging.warning(f'Failed to insert calibration frame {file_path}: {e}')
    
    # Insert light frames with target/night linkage
    for i, r in enumerate(light_rows, 1):
        target = r.get('target')
        dateobs = r.get('dateobs') or date.today().isoformat()
        telescope = r.get('telescope')
        file_path = r.get('file_path')
        
        # Check if observation already exists
        cur.execute('SELECT observation_id FROM observations WHERE file_path = ?', (file_path,))
        if cur.fetchone():
            skipped += 1
            continue
        
        try:
            # Ensure target exists
            target_id = get_or_create_target(cur, target)
            
            # Ensure night exists
            night_id = get_or_create_night(cur, dateobs, telescope)
            
            # Link target to night
            insert_scheduled_target(cur, night_id, target_id, telescope, r.get('source_path'), dry_run=False)
            
            # Insert observation
            cur.execute('''
                INSERT INTO observations (
                    scheduled_target_id, file_path, file_name, exposure_time_sec,
                    filter_name, temperature_c, binning, gain, offset
                )
                SELECT scheduled_target_id, ?, ?, ?, ?, ?, ?, ?, ?
                FROM scheduled_targets
                WHERE night_id = ? AND target_id = ?
                LIMIT 1
            ''', (
                file_path,
                r.get('file_name'),
                r.get('exptime'),
                r.get('filter'),
                r.get('temp'),
                r.get('binning'),
                r.get('gain'),
                r.get('offset'),
                night_id,
                target_id
            ))
            inserted += 1
            if i % 100 == 0:
                logging.info(f'Inserted {i}/{len(light_rows)} light frames...')
                conn.commit()  # Commit every 100 frames so progress is visible
        except Exception as e:
            logging.warning(f'Failed to insert light frame {file_path}: {e}')
    
    conn.commit()
    conn.close()
    
    logging.info(f'Database insertion complete: {inserted} new, {skipped} existing')
    return inserted


def main():
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    dbp = Path(args.db)
    all_rows = []
    
    # If --date-dir is specified, scan just that directory
    if args.date_dir:
        date_path = Path(args.date_dir)
        logging.info('Running direct scan of date directory: %s', date_path)
        # Extract date from directory name for metadata
        dateobs = parse_date_dirname(date_path.name)
        
        # Scan frame type directories directly
        frame_types = ['LIGHT', 'FLAT', 'BIAS', 'DARK']
        for frame_type in frame_types:
            frame_dir = date_path / frame_type
            if not frame_dir.exists():
                alt = date_path / frame_type.lower()
                if alt.exists() and alt.is_dir():
                    frame_dir = alt
                else:
                    continue
            
            if frame_dir.is_dir():
                try:
                    # Check if there are subdirectories or files directly in frame_dir
                    subdirs = [d for d in frame_dir.iterdir() if d.is_dir()]
                    
                    if subdirs:
                        # Scan subdirectories (normal case)
                        for subdir in sorted(subdirs):
                            fits_files = scan_fits_files(subdir, read_headers=True, frame_type=frame_type)
                            
                            for fits_info in fits_files:
                                target_name = subdir.name
                                
                                if frame_type == 'LIGHT':
                                    if args.strip_sub_suffix:
                                        target_name = re.sub(r'(_sub)(?:_.*)?$', '', target_name, flags=re.IGNORECASE)
                                elif frame_type == 'FLAT':
                                    filter_name = fits_info.get('filter') or subdir.name
                                    target_name = f'FLAT_{filter_name}'
                                elif frame_type == 'BIAS':
                                    target_name = 'BIAS'
                                elif frame_type == 'DARK':
                                    exp = fits_info.get('exptime')
                                    if exp:
                                        target_name = f'DARK_{int(exp)}s'
                                    else:
                                        target_name = f'DARK_{subdir.name}'
                                
                                all_rows.append({
                                    'target': target_name,
                                    'dateobs': dateobs,
                                    'telescope': 'SCT',
                                    'frame_type': frame_type,
                                    'source_path': str(subdir),
                                    **fits_info
                                })
                    else:
                        # No subdirectories - scan files directly in frame_dir
                        fits_files = scan_fits_files(frame_dir, read_headers=True, frame_type=frame_type)
                        
                        for fits_info in fits_files:
                            if frame_type == 'FLAT':
                                filter_name = fits_info.get('filter') or 'Unknown'
                                target_name = f'FLAT_{filter_name}'
                            elif frame_type == 'BIAS':
                                target_name = 'BIAS'
                            elif frame_type == 'DARK':
                                exp = fits_info.get('exptime')
                                if exp:
                                    target_name = f'DARK_{int(exp)}s'
                                else:
                                    target_name = 'DARK'
                            else:
                                target_name = frame_type
                            
                            all_rows.append({
                                'target': target_name,
                                'dateobs': dateobs,
                                'telescope': 'SCT',
                                'frame_type': frame_type,
                                'source_path': str(frame_dir),
                                **fits_info
                            })
                except Exception as e:
                    logging.warning('Failed listing %s dir %s: %s', frame_type, frame_dir, e)
    else:
        if args.mode in ('light', 'both'):
            bp = Path(args.base_path)
            logging.info('Running LIGHT scan under %s', bp)
            all_rows.extend(find_light_subdirs(bp, strip_sub_suffix=args.strip_sub_suffix))
        
        if args.mode in ('seestar', 'both'):
            sp = Path(args.seestar_path)
            logging.info('Running Seestar scan under %s', sp)
            all_rows.extend(scan_seestar(sp, strip_sub_suffix=args.strip_sub_suffix))
    
    logging.info('Total candidates found: %d', len(all_rows))
    process_rows(all_rows, dbp, dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
