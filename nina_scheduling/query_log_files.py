#!/usr/bin/env python3
"""
Query NINA log file imports by date.

Usage:
    python query_log_files.py nina.sqlite
    python query_log_files.py nina.sqlite --date 2025-10-24
    python query_log_files.py nina.sqlite --telescope "SCT 8-inch"
"""

import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def query_log_files(db_path: Path, observation_date: str = None, telescope: str = None):
    """Query imported log files."""
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query
    where_clauses = []
    params = []
    
    if observation_date:
        where_clauses.append("observation_date = ?")
        params.append(observation_date)
    
    if telescope:
        where_clauses.append("telescope = ?")
        params.append(telescope)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Query log files
    cursor.execute(f'''
        SELECT 
            log_filename,
            telescope,
            profile_id,
            observation_date,
            first_exposure,
            last_exposure,
            exposure_count,
            imported_at
        FROM nina_log_files
        WHERE {where_sql}
        ORDER BY observation_date DESC, first_exposure ASC
    ''', params)
    
    log_files = cursor.fetchall()
    
    if not log_files:
        print("No log files found matching criteria")
        return
    
    print(f"\nFound {len(log_files)} log file(s):\n")
    
    for log in log_files:
        print(f"📄 {log['log_filename']}")
        print(f"   Telescope: {log['telescope']}")
        print(f"   Profile ID: {log['profile_id']}")
        print(f"   Date: {log['observation_date']}")
        print(f"   Time Range: {log['first_exposure']} to {log['last_exposure']}")
        print(f"   Exposures: {log['exposure_count']}")
        print(f"   Imported: {log['imported_at']}")
        print()
    
    # Group by observation date
    cursor.execute(f'''
        SELECT 
            observation_date,
            COUNT(*) as log_count,
            SUM(exposure_count) as total_exposures
        FROM nina_log_files
        WHERE {where_sql}
        GROUP BY observation_date
        ORDER BY observation_date DESC
    ''', params)
    
    by_date = cursor.fetchall()
    
    if len(by_date) > 1:
        print("\nSummary by Date:")
        for row in by_date:
            print(f"  {row['observation_date']}: {row['log_count']} log file(s), {row['total_exposures']} exposures")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Query imported NINA log files')
    parser.add_argument('database', type=Path, help='Path to SQLite database')
    parser.add_argument('--date', help='Filter by observation date (YYYY-MM-DD)')
    parser.add_argument('--telescope', help='Filter by telescope name')
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"Error: Database not found: {args.database}")
        return 1
    
    query_log_files(args.database, args.date, args.telescope)
    return 0


if __name__ == '__main__':
    exit(main())
