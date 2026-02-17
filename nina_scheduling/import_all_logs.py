#!/usr/bin/env python3
"""Import all NINA logs from logexploit/zzz_logfiles with proper FK integration."""

import sys
from pathlib import Path

# Add logexploit to path
sys.path.insert(0, str(Path(__file__).parent.parent / "logexploit" / "src"))

from logexploit.parser import NINALogParser
from logexploit.nina_adapter import NINASchedulingAdapter

def main():
    # Configuration
    db_path = Path("Z:/scheduled_observations.sqlite")
    log_dir = Path(__file__).parent.parent / "logexploit" / "zzz_logfiles"
    telescope = "SCT 8-inch"
    
    # Find all log files
    log_files = sorted(log_dir.glob("*.log"))
    
    print(f"Found {len(log_files)} log files")
    print(f"Database: {db_path}")
    print(f"Telescope: {telescope}\n")
    
    # Process each log file
    total_imported = 0
    total_linked = 0
    errors = 0
    
    # Create single adapter instance for all files
    adapter = NINASchedulingAdapter(str(db_path), telescope)
    adapter.connect()
    
    try:
        for i, log_file in enumerate(log_files, 1):
            try:
                print(f"[{i}/{len(log_files)}] {log_file.name}", end="... ")
                
                # Parse log file
                parser = NINALogParser(log_file)
                parser.parse()
                
                targets = list(parser.targets.values())
                exposures = parser.exposures
                
                if not targets and not exposures:
                    print("SKIP (no data)")
                    continue
                
                # Import with NINA integration
                stats = adapter.store_session(log_file, targets, exposures)
                
                total_imported += stats['exposures_imported']
                total_linked += stats['scheduled_links']
                
                print(f"OK ({stats['exposures_imported']} exp, {stats['scheduled_links']} linked)")
                
            except Exception as e:
                errors += 1
                print(f"ERROR: {e}")
    
    finally:
        # Close adapter
        adapter.disconnect()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Files processed: {len(log_files) - errors}")
    print(f"Files failed: {errors}")
    print(f"Exposures imported: {total_imported}")
    print(f"Linked to scheduled: {total_linked}")
    print(f"\nDatabase: {db_path}")

if __name__ == "__main__":
    main()
