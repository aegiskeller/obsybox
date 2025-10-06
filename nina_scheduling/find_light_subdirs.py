#!/usr/bin/env python3
"""
Scan a base path (default: D:\) and for each immediate child directory look for a
subdirectory named 'LIGHT'. If found, record the names of all subdirectories
inside that 'LIGHT' directory.

Outputs a CSV (default) or JSON containing rows with:
- parent_dir: the directory under the base path that contains LIGHT
- light_path: full path to the LIGHT directory
- subdir: name of a subdirectory inside LIGHT

Usage examples:
  python find_light_subdirs.py                 # scans D:\ and writes light_subdirs.csv
  python find_light_subdirs.py --base-path C:\ --out results.json --format json
  python find_light_subdirs.py --base-path . --out nina_light.csv

The script is conservative about permissions and will skip unreadable folders.
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
    p = argparse.ArgumentParser(description='Find subdirectories inside LIGHT folders under each child of a base path.')
    p.add_argument('--base-path', default='D:\\', help='Base path to scan (default: D:\\)')
    # database options
    p.add_argument('--db', default='observations.sqlite', help='Path to SQLite database to write results (default observations.sqlite)')
    p.add_argument('--telescope', default='SCT', help='Telescope name to record in the observations table (default: SCT)')
    p.add_argument('--dateobs', default=None, help='Observation date to record (YYYY-MM-DD). Defaults to today')
    p.add_argument('--dry-run', action='store_true', help='Do not write to DB; just print what would be inserted')
    p.add_argument('--format', choices=('csv', 'json'), help='(Deprecated) Force output format (overrides extension)')
    p.add_argument('--out', default='light_subdirs.csv', help='(Deprecated) Output filename (CSV or JSON by extension)')
    p.add_argument('--verbose', action='store_true')
    return p.parse_args()


def ensure_observations_table(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY,
        target TEXT NOT NULL,
        dateobs DATE,
        telescope TEXT,
        processed DATETIME,
        UNIQUE(target, dateobs)
    )
    ''')
    conn.commit()
    return conn


def write_to_db(rows, db_path: Path, telescope: str, dateobs: str, dry_run: bool = False):
    """Write discovered rows into the observations table. target is the full path to the subdir inside LIGHT."""
    if not rows:
        logging.info('No rows to insert into DB')
        return 0
    # don't overwrite per-row dateobs; dateobs param is fallback
    today_iso = date.today().isoformat()
    inserted = 0
    if dry_run:
        for r in rows:
            # target will be the subdir name only
            target = r['subdir']
            row_dateobs = r.get('dateobs') or dateobs or today_iso
            print(f'Would insert: target={target} dateobs={row_dateobs} telescope={telescope or None}')
        return 0

    conn = ensure_observations_table(Path(db_path))
    cur = conn.cursor()
    try:
        for r in rows:
            # store only the subdir name as the target
            target = r['subdir']
            row_dateobs = r.get('dateobs') or dateobs or today_iso
            try:
                cur.execute('INSERT OR IGNORE INTO observations (target, dateobs, telescope, processed) VALUES (?, ?, ?, ?)',
                            (target, row_dateobs, telescope or None, None))
                if cur.rowcount:
                    inserted += 1
            except Exception as e:
                logging.warning('Failed to insert %s: %s', target, e)
        conn.commit()
    finally:
        conn.close()
    logging.info('Inserted %d new rows into %s', inserted, db_path)
    return inserted


def main():
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    base = Path(args.base_path)
    out = Path(args.out)
    fmt = args.format
    if fmt is None:
        if out.suffix.lower() == '.json':
            fmt = 'json'
        else:
            fmt = 'csv'

    logging.info("Scanning base path: %s", base)
    rows = find_light_subdirs(base)
    logging.info("Found %d subdirectories inside LIGHT folders", len(rows))

    # If a DB path is provided (default is observations.sqlite), write to DB
    if args.db:
        # Use per-row dateobs where available; args.dateobs is fallback
        if args.dry_run:
            write_to_db(rows, Path(args.db), args.telescope, args.dateobs, dry_run=True)
        else:
            inserted = write_to_db(rows, Path(args.db), args.telescope, args.dateobs, dry_run=False)
            logging.info('Inserted %d rows into %s', inserted, args.db)
        return 0

    # Fallback: write CSV/JSON (deprecated path)
    if fmt == 'csv':
        write_csv(rows, out)
    else:
        write_json(rows, out)

    logging.info("Wrote results to %s", out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
