#!/usr/bin/env python3
"""
Observation Crawler - Post-processing script to enrich observation metadata

This script crawls through the observations table and populates additional metadata
from FITS headers that wasn't captured during initial import:

- Timing: datetime_start, datetime_end, julian_date
- Guiding: guiding_enabled, guiding_rms_arcsec, guiding_rms_ra_arcsec, guiding_rms_dec_arcsec
- Image quality: fwhm_arcsec, hfr, eccentricity, stars_detected, background_adu
- Environmental: humidity_percent, pressure_mbar (if available)
- Telescope state: telescope_ra, telescope_dec, telescope_alt, telescope_az, airmass
- Processing flags: calibrated, plate_solved, quality_flag

Usage:
  # Process all observations missing metadata
  python observation_crawler.py
  
  # Process specific observation night
  python observation_crawler.py --date 2025-10-24
  
  # Dry run to see what would be updated
  python observation_crawler.py --dry-run
  
  # Process only specific fields
  python observation_crawler.py --fields timing,quality
"""

from pathlib import Path
import argparse
import logging
import sqlite3
import sys
import shutil
from datetime import datetime

try:
    from astropy.io import fits
    from astropy.time import Time
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord
    import astropy.units as u
    HAVE_ASTROPY = True
except ImportError:
    HAVE_ASTROPY = False
    logging.warning("astropy not available - some features will be disabled")

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def parse_args():
    p = argparse.ArgumentParser(description='Crawl observations and populate metadata from FITS headers')
    p.add_argument('--db', default='D:\\scheduled_observations.sqlite', 
                   help='Path to SQLite database')
    p.add_argument('--date', help='Process only observations from this date (YYYY-MM-DD)')
    p.add_argument('--telescope', help='Process only observations from this telescope')
    p.add_argument('--dry-run', action='store_true', 
                   help='Show what would be updated without writing to database')
    p.add_argument('--fields', 
                   help='Comma-separated list of field groups to update (timing,guiding,quality,environment,telescope,processing)')
    p.add_argument('--force', action='store_true',
                   help='Update even if metadata already exists')
    p.add_argument('--batch-size', type=int, default=100,
                   help='Commit every N observations (default: 100)')
    p.add_argument('--quarantine-dir', default='D:\\quarantine',
                   help='Directory to move problematic files (default: D:\\quarantine)')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def read_fits_metadata(fits_path: Path):
    """Read comprehensive metadata from FITS file.
    
    Returns dict with all available metadata fields from FITS header.
    Raises FileNotFoundError if file doesn't exist.
    """
    if not HAVE_ASTROPY:
        return {}
    
    if not fits_path.exists():
        raise FileNotFoundError(f"File not found: {fits_path}")
    
    try:
        with fits.open(str(fits_path), ignore_missing_simple=True, memmap=False) as hdul:
            if len(hdul) == 0:
                return {}
            
            header = hdul[0].header
            data = hdul[0].data
            
            metadata = {}
            
            # === TIMING ===
            date_obs = header.get('DATE-OBS')
            if date_obs:
                metadata['datetime_start'] = date_obs
                
                # Calculate end time if exposure time available
                exptime = header.get('EXPTIME', header.get('EXPOSURE'))
                if exptime and date_obs:
                    try:
                        t = Time(date_obs, format='isot', scale='utc')
                        t_end = t + exptime * u.second
                        metadata['datetime_end'] = t_end.isot
                        # Julian date at mid-exposure
                        t_mid = t + (exptime / 2.0) * u.second
                        metadata['julian_date'] = t_mid.jd
                    except:
                        pass
            
            # === GUIDING ===
            metadata['guiding_enabled'] = header.get('GUIDING', None)
            metadata['guiding_rms_arcsec'] = header.get('GUIDERMS', header.get('GUIDE_RMS'))
            metadata['guiding_rms_ra_arcsec'] = header.get('GUIDERRA', header.get('GUIDE_RA'))
            metadata['guiding_rms_dec_arcsec'] = header.get('GUIDERDE', header.get('GUIDE_DEC'))
            
            # === IMAGE QUALITY ===
            metadata['fwhm_arcsec'] = header.get('FWHM')
            metadata['hfr'] = header.get('HFR')
            metadata['eccentricity'] = header.get('ECCENT', header.get('ECCENTRICITY'))
            metadata['stars_detected'] = header.get('NSTARS', header.get('STARS'))
            
            # Background level
            if data is not None:
                try:
                    import numpy as np
                    # Use median of bottom 10% of pixel values as background estimate
                    metadata['background_adu'] = float(np.percentile(data, 10))
                except:
                    pass
            
            # === ENVIRONMENTAL ===
            metadata['humidity_percent'] = header.get('HUMIDITY')
            metadata['pressure_mbar'] = header.get('PRESSURE')
            
            # === TELESCOPE STATE ===
            # Coordinates
            ra = header.get('RA', header.get('OBJCTRA'))
            dec = header.get('DEC', header.get('OBJCTDEC'))
            
            # Convert RA/DEC to degrees if in HMS/DMS format
            if ra and isinstance(ra, str):
                try:
                    coord = SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
                    metadata['telescope_ra'] = coord.ra.deg
                    metadata['telescope_dec'] = coord.dec.deg
                except:
                    pass
            elif ra and isinstance(ra, (int, float)):
                metadata['telescope_ra'] = float(ra)
                metadata['telescope_dec'] = float(dec) if dec else None
            
            # Alt/Az
            metadata['telescope_alt'] = header.get('CENTALT', header.get('ALTITUDE', header.get('OBJCTALT')))
            metadata['telescope_az'] = header.get('CENTAZ', header.get('AZIMUTH', header.get('OBJCTAZ')))
            metadata['airmass'] = header.get('AIRMASS')
            
            # Calculate airmass from altitude if not in header
            if metadata.get('telescope_alt') and not metadata.get('airmass'):
                try:
                    alt = float(metadata['telescope_alt'])
                    # Airmass = sec(zenith angle) = 1/sin(altitude)
                    import math
                    airmass = 1.0 / math.sin(math.radians(alt))
                    metadata['airmass'] = airmass
                except:
                    pass
            
            # === FILE INFO ===
            metadata['file_size_bytes'] = fits_path.stat().st_size
            metadata['file_format'] = 'FITS'
            
            # Remove None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            return metadata
            
    except Exception as e:
        logging.debug(f"Failed to read FITS metadata from {fits_path.name}: {e}")
        raise  # Re-raise to allow caller to handle quarantine


def quarantine_file(fits_path: Path, error_msg: str, obs_info: dict, quarantine_dir: Path):
    """Move problematic file to quarantine with error details.
    
    For missing files, creates the error log without the actual file.
    """
    try:
        # Create quarantine directory if it doesn't exist
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectory by date if available
        date_str = obs_info.get('date_obs', 'unknown_date')
        telescope = obs_info.get('telescope', 'unknown_telescope')
        subdir = quarantine_dir / f"{date_str}_{telescope}"
        subdir.mkdir(parents=True, exist_ok=True)
        
        # Only copy file if it exists
        if fits_path.exists():
            dest_file = subdir / fits_path.name
            shutil.copy2(str(fits_path), str(dest_file))
            logging.info(f"  Quarantined: {fits_path.name} -> {subdir}")
        else:
            logging.info(f"  Logging missing file: {fits_path.name}")
        
        # Create error details file
        file_name = obs_info.get('file_name', fits_path.name)
        error_file = subdir / f"{Path(file_name).stem}_ERROR.txt"
        with open(error_file, 'w') as f:
            f.write(f"QUARANTINED FILE: {file_name}\n")
            f.write(f"Original Path: {fits_path}\n")
            f.write(f"File Exists: {fits_path.exists()}\n")
            f.write(f"Quarantine Time: {datetime.now().isoformat()}\n")
            f.write(f"Observation Date: {obs_info.get('date_obs', 'N/A')}\n")
            f.write(f"Telescope: {obs_info.get('telescope', 'N/A')}\n")
            f.write(f"Observation ID: {obs_info.get('observation_id', 'N/A')}\n")
            f.write(f"\nERROR DETAILS:\n")
            f.write(f"{error_msg}\n")
        
        # Remove original file only if it exists and was successfully copied
        if fits_path.exists():
            fits_path.unlink()
            logging.info(f"  Removed original: {fits_path}")
        
        return True
    except Exception as e:
        logging.error(f"  Failed to quarantine {fits_path.name}: {e}")
        return False


def get_observations_to_process(conn, args):
    """Get list of observations that need metadata enrichment."""
    
    cur = conn.cursor()
    
    query = '''
        SELECT o.observation_id, o.file_path, o.file_name, 
               o.datetime_start, o.julian_date, o.fwhm_arcsec,
               n.date_obs, n.telescope
        FROM observations o
        JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id
        JOIN observation_nights n ON st.night_id = n.night_id
        WHERE 1=1
    '''
    params = []
    
    if args.date:
        query += ' AND n.date_obs = ?'
        params.append(args.date)
    
    if args.telescope:
        query += ' AND n.telescope = ?'
        params.append(args.telescope)
    
    # Only process if missing key metadata (unless --force)
    if not args.force:
        query += ' AND (o.datetime_start IS NULL OR o.julian_date IS NULL)'
    
    query += ' ORDER BY n.date_obs, o.observation_id'
    
    cur.execute(query, params)
    return cur.fetchall()


def update_observation_metadata(conn, observation_id, metadata, args, dry_run=False):
    """Update observation record with enriched metadata."""
    
    if not metadata:
        return False
    
    # Filter by requested field groups if specified
    if args.fields:
        field_groups = {
            'timing': ['datetime_start', 'datetime_end', 'julian_date'],
            'guiding': ['guiding_enabled', 'guiding_rms_arcsec', 'guiding_rms_ra_arcsec', 'guiding_rms_dec_arcsec'],
            'quality': ['fwhm_arcsec', 'hfr', 'eccentricity', 'stars_detected', 'background_adu'],
            'environment': ['humidity_percent', 'pressure_mbar'],
            'telescope': ['telescope_ra', 'telescope_dec', 'telescope_alt', 'telescope_az', 'airmass'],
            'processing': ['file_size_bytes', 'file_format']
        }
        
        requested = set(args.fields.split(','))
        allowed_fields = set()
        for group in requested:
            if group in field_groups:
                allowed_fields.update(field_groups[group])
        
        metadata = {k: v for k, v in metadata.items() if k in allowed_fields}
    
    if not metadata:
        return False
    
    if dry_run:
        return True
    
    # Build UPDATE statement
    set_clause = ', '.join([f"{k} = ?" for k in metadata.keys()])
    values = list(metadata.values()) + [observation_id]
    
    query = f"UPDATE observations SET {set_clause} WHERE observation_id = ?"
    
    cur = conn.cursor()
    cur.execute(query, values)
    
    return True


def main():
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not HAVE_ASTROPY:
        logging.error("astropy is required for observation crawler")
        return 1
    
    db_path = Path(args.db)
    if not db_path.exists():
        logging.error(f"Database not found: {db_path}")
        return 1
    
    quarantine_dir = Path(args.quarantine_dir)
    
    conn = sqlite3.connect(str(db_path))
    
    # Get observations to process
    observations = get_observations_to_process(conn, args)
    logging.info(f"Found {len(observations)} observations to process")
    
    if not observations:
        logging.info("No observations need processing")
        return 0
    
    if args.dry_run:
        logging.info("DRY RUN - No changes will be made")
    
    processed = 0
    updated = 0
    errors = 0
    quarantined = 0
    
    for i, obs in enumerate(observations, 1):
        obs_id, file_path, file_name, dt_start, jd, fwhm, date_obs, telescope = obs
        
        logging.info(f"[{i}/{len(observations)}] Processing {file_name} ({date_obs}, {telescope})")
        
        # Read metadata from FITS file
        fits_path = Path(file_path)
        
        try:
            metadata = read_fits_metadata(fits_path)
            
            if metadata:
                if args.dry_run:
                    print(f"  Would update observation {obs_id} with:")
                    for k, v in metadata.items():
                        print(f"    {k}: {v}")
                else:
                    if update_observation_metadata(conn, obs_id, metadata, args, dry_run=False):
                        updated += 1
                        
                        # Commit periodically
                        if updated % args.batch_size == 0:
                            conn.commit()
                            logging.info(f"  Committed {updated} updates...")
            else:
                logging.warning(f"  No metadata extracted from {file_name}")
                errors += 1
                
        except Exception as e:
            error_msg = f"Failed to read FITS metadata: {str(e)}"
            logging.warning(f"  {error_msg}")
            errors += 1
            
            # Quarantine the problematic file
            if not args.dry_run:
                obs_info = {
                    'observation_id': obs_id,
                    'date_obs': date_obs,
                    'telescope': telescope,
                    'file_name': file_name
                }
                if quarantine_file(fits_path, error_msg, obs_info, quarantine_dir):
                    quarantined += 1
        
        processed += 1
    
    if not args.dry_run:
        conn.commit()
        logging.info(f"Final commit complete")
    
    conn.close()
    
    logging.info(f"\nProcessing complete:")
    logging.info(f"  Processed: {processed}")
    logging.info(f"  Updated: {updated}")
    logging.info(f"  Errors: {errors}")
    logging.info(f"  Quarantined: {quarantined}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
