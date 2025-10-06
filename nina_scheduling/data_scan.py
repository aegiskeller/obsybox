#!/usr/bin/env python3
"""
Unified data scanner: merges find_light_subdirs and scan_seestar functionality.

Modes:
 - light: scan immediate children of --base-path for a LIGHT subdirectory and record subdirs
 - seestar: scan --seestar-path for yyyymmdd folders and record their subdirs
 - both: run both scans

Behavior:
 - Writes to observations SQLite DB (default observations.sqlite)
 - Ensures observations table exists with UNIQUE(target,dateobs)
 - Before inserting, checks if (target,dateobs) already exists and skips to avoid duplicates
 - By default, target is the subdirectory name; trailing '_sub' and any suffix after it is stripped
 - Default telescopes: light -> 'SCT', seestar -> 'S50'
"""
from pathlib import Path
import argparse
import logging
import re
import sqlite3
from datetime import date
import sys

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Reuse but re-declare ensure_observations_table to avoid import cycles
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
    # create index for faster existence checks
    cur.execute('CREATE INDEX IF NOT EXISTS idx_obs_target_date ON observations(target, dateobs)')
    conn.commit()
    return conn


def parse_args():
    p = argparse.ArgumentParser(description='Unified scanner for LIGHT and Seestar data into observations DB')
    p.add_argument('--mode', choices=('light', 'seestar', 'both'), default='both', help='Which scans to run')
    p.add_argument('--base-path', default='D:\\', help='Base path to scan for LIGHT (default D:\\)')
    p.add_argument('--seestar-path', default='D:\\Seestar', help='Path to scan for Seestar date folders (default D:\\Seestar)')
    p.add_argument('--db', default='observations.sqlite', help='SQLite DB path')
    p.add_argument('--dry-run', action='store_true', help='Do not write to DB; show actions')
    p.add_argument('--verbose', action='store_true')
    p.add_argument('--strip-sub-suffix', action='store_true', default=True,
                   help='Strip trailing _sub and any following suffixes (e.g., _sub_d -> remove)')
    return p.parse_args()


def find_light_subdirs(base_path: Path, strip_sub_suffix: bool = True):
    """Scan immediate child directories of base_path for a LIGHT folder and return rows.
    Each row is dict: target, dateobs, telescope
    dateobs: attempt to parse parent directory name as yyyy-mm-dd, else None
    target: subdirectory name (stripped if requested)
    telescope: 'SCT'
    """
    results = []
    if not base_path.exists() or not base_path.is_dir():
        logging.warning('Base path %s missing or not a dir', base_path)
        return results

    for child in sorted(base_path.iterdir()):
        if not child.is_dir():
            continue
        light_dir = child / 'LIGHT'
        if not light_dir.exists():
            alt = child / 'light'
            if alt.exists() and alt.is_dir():
                light_dir = alt
            else:
                continue
        if not light_dir.is_dir():
            continue
        # parse date from parent dir name if in yyyy-mm-dd
        dir_name = child.name
        dateobs = None
        if re.match(r'^\d{4}-\d{2}-\d{2}$', dir_name):
            try:
                # validate
                _ = date.fromisoformat(dir_name)
                dateobs = dir_name
            except Exception:
                dateobs = None
        try:
            for entry in sorted(light_dir.iterdir()):
                if entry.is_dir():
                    t = entry.name
                    if strip_sub_suffix:
                        # remove _sub and anything after it
                        t = re.sub(r'(_sub)(?:_.*)?$', '', t, flags=re.IGNORECASE)
                    results.append({'target': t, 'dateobs': dateobs, 'telescope': 'SCT', 'source_path': str(entry)})
        except Exception as e:
            logging.warning('Failed listing LIGHT dir %s: %s', light_dir, e)
    return results


def parse_yyyymmdd(name: str):
    if re.match(r'^\d{8}$', name):
        try:
            yyyy = name[0:4]; mm = name[4:6]; dd = name[6:8]
            iso = f"{yyyy}-{mm}-{dd}"
            _ = date.fromisoformat(iso)
            return iso
        except Exception:
            return None
    return None


def scan_seestar(seestar_path: Path, strip_sub_suffix: bool = True):
    results = []
    if not seestar_path.exists() or not seestar_path.is_dir():
        logging.warning('Seestar path %s missing or not a dir', seestar_path)
        return results
    for child in sorted(seestar_path.iterdir()):
        if not child.is_dir():
            continue
        dateobs = parse_yyyymmdd(child.name)
        if not dateobs:
            continue
        try:
            for sub in sorted(child.iterdir()):
                if not sub.is_dir():
                    continue
                t = sub.name
                if strip_sub_suffix:
                    t = re.sub(r'(_sub)(?:_.*)?$', '', t, flags=re.IGNORECASE)
                results.append({'target': t, 'dateobs': dateobs, 'telescope': 'S50', 'source_path': str(sub)})
        except Exception as e:
            logging.warning('Failed listing Seestar date dir %s: %s', child, e)
    return results


def insert_rows(rows, db_path: Path, dry_run: bool = False):
    if not rows:
        logging.info('No rows to insert')
        return 0
    conn = ensure_observations_table(db_path)
    cur = conn.cursor()
    inserted = 0
    for r in rows:
        target = r['target']
        dateobs = r['dateobs'] or date.today().isoformat()
        telescope = r.get('telescope')
        # existence check
        cur.execute('SELECT 1 FROM observations WHERE target = ? AND dateobs = ?', (target, dateobs))
        if cur.fetchone():
            logging.debug('Skipping existing %s %s', target, dateobs)
            continue
        if dry_run:
            print(f'Would insert: target={target} dateobs={dateobs} telescope={telescope}')
            continue
        try:
            cur.execute('INSERT INTO observations (target, dateobs, telescope, processed) VALUES (?, ?, ?, ?)',
                        (target, dateobs, telescope, None))
            inserted += 1
        except Exception as e:
            logging.warning('Failed to insert %s %s: %s', target, dateobs, e)
    conn.commit()
    conn.close()
    logging.info('Inserted %d new rows into %s', inserted, db_path)
    return inserted


def main():
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    dbp = Path(args.db)
    all_rows = []
    if args.mode in ('light', 'both'):
        bp = Path(args.base_path)
        logging.info('Running LIGHT scan under %s', bp)
        all_rows.extend(find_light_subdirs(bp, strip_sub_suffix=args.strip_sub_suffix))
    if args.mode in ('seestar', 'both'):
        sp = Path(args.seestar_path)
        logging.info('Running Seestar scan under %s', sp)
        all_rows.extend(scan_seestar(sp, strip_sub_suffix=args.strip_sub_suffix))

    logging.info('Total candidates found: %d', len(all_rows))
    if args.dry_run:
        insert_rows(all_rows, dbp, dry_run=True)
    else:
        insert_rows(all_rows, dbp, dry_run=False)


if __name__ == '__main__':
    sys.exit(main())
