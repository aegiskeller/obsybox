#!/usr/bin/env python3
"""
Download a CDS Vizier catalog and store it in a local SQLite database optimized for
searching and modification.

Function: download_vizier_catalog(catalog='wcs', sqlite_path='wcs_catalog.sqlite',
                                  table_name='wcs', index_cols=None, force=False, row_limit=-1)

- catalog: Vizier catalog identifier or name (string). Example: 'B/wds/wds' or 'wcs'.
- sqlite_path: path to output SQLite file
- table_name: SQL table name to store rows
- index_cols: list of column names to create indexes on (optional)
- force: if True, overwrite existing sqlite file/table
- row_limit: if >0, limit rows downloaded (useful for testing)

The function will try to use pandas for fast writing to SQLite. If pandas is not
available, it will fall back to writing the table out as ECSV (astropy) and CSV.

It returns a dict with metadata about the saved file (rows, path, indexes).
"""
#  e.g. cd C:\Users\Admin\Documents\Arduino\obsybox\nina_scheduling
#  python .\download_wds.py --catalog 'B/wds/wds' --force --rows -1 --sqlite wds_catalog.sqlite --table wds -i RAJ2000 -i DEJ2000 -i WDS


from typing import Optional, List, Dict, Any
import os
import sqlite3
import json
import datetime

try:
    from astroquery.vizier import Vizier
    from astropy.table import Table
    import astropy.units as u
    ASTRO_PKG = True
except Exception as e:
    ASTRO_PKG = False

# pandas is optional but highly recommended for SQLite writing
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    PANDAS_AVAILABLE = False


def download_vizier_catalog(catalog: str = 'wcs',
                            sqlite_path: str = 'wcs_catalog.sqlite',
                            table_name: str = 'wcs',
                            index_cols: Optional[List[str]] = None,
                            force: bool = False,
                            row_limit: int = -1) -> Dict[str, Any]:
    """
    Download a Vizier catalog and store in SQLite (preferred) or fallback formats.

    Returns metadata dict: {'sqlite_path': ..., 'table': ..., 'rows': N, 'indexes': [...]}
    """
    if not ASTRO_PKG:
        raise RuntimeError("Required packages not installed: astroquery/astropy")

    print(f"Downloading Vizier catalog '{catalog}' (row_limit={row_limit})...")

    v = Vizier(columns=['*'])
    # If user requested a partial download for testing, set ROW_LIMIT
    v.ROW_LIMIT = row_limit if row_limit and row_limit > 0 else -1

    try:
        catalog_list = v.get_catalogs(catalog)
        if len(catalog_list) == 0:
            raise RuntimeError(f"No catalogs returned for '{catalog}'")
        atbl = catalog_list[0]
    except Exception as e:
        raise RuntimeError(f"Error retrieving catalog '{catalog}': {e}")

    # Convert Astropy Table to pandas DataFrame if possible
    df = None
    if PANDAS_AVAILABLE:
        try:
            # astropy Table to pandas handles masked values
            df = atbl.to_pandas()
        except Exception as e:
            print(f"Warning: conversion to pandas failed: {e}")
            df = None

    timestamp = datetime.datetime.utcnow().isoformat()

    # If pandas available, write to SQLite using to_sql
    if df is not None:
        # Create/overwrite SQLite database or table as requested
        conn = sqlite3.connect(sqlite_path)
        if_exists_mode = 'replace' if force else 'fail'
        try:
            df.to_sql(table_name, conn, if_exists=if_exists_mode, index=False)
        except ValueError as e:
            # Table exists and force not True
            if 'already exists' in str(e) and force:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            else:
                conn.close()
                raise

        # Create indexes if requested
        created_indexes = []
        if index_cols:
            cur = conn.cursor()
            for col in index_cols:
                safe_col = ''.join(c for c in col if c.isalnum() or c == '_')
                idx_name = f"idx_{table_name}_{safe_col}"
                try:
                    cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({col})")
                    created_indexes.append(idx_name)
                except Exception as e:
                    print(f"Warning: could not create index on {col}: {e}")
            conn.commit()
        # Get row count
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        rows = cur.fetchone()[0]
        conn.close()

        meta = {
            'sqlite_path': os.path.abspath(sqlite_path),
            'table': table_name,
            'rows': int(rows),
            'indexes': created_indexes,
            'timestamp_utc': timestamp,
            'catalog_query': catalog
        }

        # Also save a small JSON metadata file alongside the DB
        meta_path = sqlite_path + '.meta.json'
        with open(meta_path, 'w') as mf:
            json.dump(meta, mf, indent=2)

        print(f"Saved {rows} rows into SQLite '{sqlite_path}' (table '{table_name}')")
        return meta

    # Fallback (pandas not available): write Astropy Table to ECSV and CSV
    print("Pandas not available; falling back to ECSV/CSV output")
    base, _ = os.path.splitext(sqlite_path)
    ecsv_path = base + '.ecsv'
    csv_path = base + '.csv'

    try:
        atbl.write(ecsv_path, format='ascii.ecsv')
        atbl.write(csv_path, format='csv')
        rows = len(atbl)
        meta = {
            'ecsv_path': os.path.abspath(ecsv_path),
            'csv_path': os.path.abspath(csv_path),
            'rows': int(rows),
            'timestamp_utc': timestamp,
            'catalog_query': catalog
        }
        meta_path = base + '.meta.json'
        with open(meta_path, 'w') as mf:
            json.dump(meta, mf, indent=2)
        print(f"Saved {rows} rows to '{ecsv_path}' and '{csv_path}'")
        return meta
    except Exception as e:
        raise RuntimeError(f"Failed to save fallback formats: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Download a Vizier catalog and store locally (SQLite preferred).')
    parser.add_argument('--catalog', '-c', default='wcs', help='Vizier catalog identifier (default: wcs)')
    parser.add_argument('--sqlite', '-s', default='wcs_catalog.sqlite', help='Output SQLite file path')
    parser.add_argument('--table', '-t', default='wcs', help='Table name inside SQLite DB')
    parser.add_argument('--index', '-i', action='append', help='Column to create an index on (can be repeated)')
    parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing table if present')
    parser.add_argument('--rows', '-r', type=int, default=10, help='Row limit for testing; use -1 for full download')
    args = parser.parse_args()

    # For safety by default run a small sample unless user explicitly sets rows=-1
    if args.rows == -1:
        row_limit = -1
    else:
        row_limit = args.rows

    try:
        meta = download_vizier_catalog(catalog=args.catalog, sqlite_path=args.sqlite,
                                       table_name=args.table, index_cols=args.index,
                                       force=args.force, row_limit=row_limit)
        print(json.dumps(meta, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")
        raise
