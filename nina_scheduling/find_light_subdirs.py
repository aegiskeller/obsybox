#!/usr/bin/env python3
"""
Scan a base path and find LIGHT subdirectories containing observations.

This script scans for LIGHT directories under dated folders (YYYY-MM-DD format)
and can import them into the observation database.

The new database schema properly models:
- Sequences: NINA sequence files that can be reused across nights
- Observation Nights: Individual nights with metadata
- Targets: Astronomical objects with coordinates and properties
- Scheduled Targets: Targets scheduled for specific nights
- Observations: Individual image captures with full metadata

Usage examples:
  # Import into database
  python find_light_subdirs.py --base-path D:\ --db observations.sqlite --telescope SCT
  
  # Dry run to see what would be imported
  python find_light_subdirs.py --base-path D:\ --dry-run
  
  # Legacy CSV/JSON output (deprecated)
  python find_light_subdirs.py --base-path D:\ --out results.csv
"""
from pathlib import Path
import argparse
import csv
import json
import sys
import logging
import sqlite3
from datetime import date
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def find_light_subdirs(base_path: Path):
    """Return a list of dicts for each subdirectory inside a LIGHT folder.

    Each dict has keys: parent, light, subdir
    """
    results = []
    if not base_path.exists():
        logging.error("Base path '%s' does not exist", base_path)
        return results
    if not base_path.is_dir():
        logging.error("Base path '%s' is not a directory", base_path)
        return results

    try:
        children = list(base_path.iterdir())
    except Exception as e:
        logging.error("Failed to list base path '%s': %s", base_path, e)
        return results

    for child in children:
        if not child.is_dir():
            continue
        light_dir = child / 'LIGHT'
        # also accept lowercase 'light' optionally
        if not light_dir.exists():
            light_dir_alt = child / 'light'
            if light_dir_alt.exists() and light_dir_alt.is_dir():
                light_dir = light_dir_alt
            else:
                continue
        if not light_dir.is_dir():
            continue
        try:
            for entry in sorted(light_dir.iterdir()):
                if entry.is_dir():
                    # try to parse a date from the parent directory name (yyyy-mm-dd)
                    dir_name = child.name
                    dateobs = None
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', dir_name):
                        try:
                            # validate date
                            _ = date.fromisoformat(dir_name)
                            dateobs = dir_name
                        except Exception:
                            dateobs = None
                    results.append({
                        'parent': str(child),
                        'light': str(light_dir),
                        'subdir': entry.name,
                        'dateobs': dateobs,
                    })
        except Exception as e:
            logging.warning("Could not list contents of '%s': %s", light_dir, e)
            continue
    return results


def write_csv(rows, out_path: Path):
    with out_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['parent', 'light', 'subdir'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def write_json(rows, out_path: Path):
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)


def parse_args():
    p = argparse.ArgumentParser(description='Find and import LIGHT subdirectories into observation database')
    p.add_argument('--base-path', default='D:\\', help='Base path to scan (default: D:\\)')
    
    # Database options (primary usage)
    p.add_argument('--db', default='observations.sqlite', 
                   help='Path to SQLite database (default: observations.sqlite)')
    p.add_argument('--telescope', default='SCT', 
                   help='Telescope name (default: SCT)')
    p.add_argument('--dry-run', action='store_true', 
                   help='Do not write to DB; just print what would be inserted')
    
    # Legacy CSV/JSON options (deprecated)
    p.add_argument('--format', choices=('csv', 'json'), 
                   help='(Deprecated) Force output format')
    p.add_argument('--out', default=None, 
                   help='(Deprecated) Output filename for CSV/JSON')
    
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def main():
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    base = Path(args.base_path)
    
    logging.info("Scanning base path: %s", base)
    rows = find_light_subdirs(base)
    logging.info("Found %d subdirectories inside LIGHT folders", len(rows))
    
    if not rows:
        logging.warning("No LIGHT subdirectories found")
        return 0

    # Primary usage: Import into database
    if args.db and not args.out:
        from observation_db import ObservationDB
        
        db = ObservationDB(args.db)
        
        if args.dry_run:
            logging.info("DRY RUN - No changes will be made")
            for r in rows:
                target_name = r['subdir']
                date_obs = r.get('dateobs') or 'today'
                print(f"Would import: target={target_name} date={date_obs} telescope={args.telescope}")
            return 0
        
        # Import into database
        stats = db.import_light_subdirs(base, telescope=args.telescope, dry_run=False)
        logging.info("Import complete: %s", stats)
        return 0
    
    # Legacy: write CSV/JSON if --out is specified
    if args.out:
        out = Path(args.out)
        fmt = args.format
        if fmt is None:
            fmt = 'json' if out.suffix.lower() == '.json' else 'csv'
        
        if fmt == 'csv':
            write_csv(rows, out)
        else:
            write_json(rows, out)
        
        logging.info("Wrote results to %s", out)
        return 0
    
    # Default: print summary
    print(f"\nFound {len(rows)} targets in LIGHT directories:")
    for r in rows:
        print(f"  {r['subdir']} - {r.get('dateobs', 'no date')} - {r['light']}")
    print(f"\nUse --db to import into database")
    return 0


if __name__ == '__main__':
    sys.exit(main())
