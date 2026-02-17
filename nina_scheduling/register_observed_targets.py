#!/usr/bin/env python3
"""
Register observed targets that weren't previously scheduled.

This script finds all 'unscheduled' entries in scheduled_targets
and allows you to link them to sequence files if they exist.
"""

import sys
import sqlite3
from pathlib import Path

# Add logexploit to path
sys.path.insert(0, str(Path(__file__).parent.parent / "logexploit" / "src"))
from logexploit.database import mark_targets_scheduled

def find_unscheduled_targets(db_path):
    """Find all unscheduled observations."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            t.target_id,
            t.target_name,
            n.date_obs,
            COUNT(o.observation_id) as num_exposures
        FROM scheduled_targets st
        JOIN targets t ON st.target_id = t.target_id
        JOIN observation_nights n ON st.night_id = n.night_id
        LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
        WHERE st.status = 'unscheduled'
        GROUP BY t.target_id, t.target_name, n.date_obs
        ORDER BY n.date_obs DESC, t.target_name
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def check_for_sequence_file(target_name, base_dir=None):
    """Check if a sequence JSON file exists for this target."""
    if base_dir is None:
        base_dir = Path(__file__).parent
    
    targets_dir = base_dir / "targets"
    
    # Try exact match
    exact_file = targets_dir / f"{target_name}.json"
    if exact_file.exists():
        return exact_file
    
    # Try variations (spaces, special chars)
    for json_file in targets_dir.glob("*.json"):
        if target_name.replace(" ", "").lower() in json_file.stem.replace(" ", "").lower():
            return json_file
    
    return None

def main():
    db_path = Path("Z:/scheduled_observations.sqlite")
    
    print("=" * 70)
    print("UNSCHEDULED TARGETS REPORT")
    print("=" * 70)
    print()
    
    unscheduled = find_unscheduled_targets(db_path)
    
    if not unscheduled:
        print("No unscheduled targets found!")
        return
    
    print(f"Found {len(unscheduled)} unscheduled target observations:\n")
    
    # Group by target
    targets_summary = {}
    for row in unscheduled:
        target_name = row['target_name']
        if target_name not in targets_summary:
            targets_summary[target_name] = {
                'target_id': row['target_id'],
                'nights': [],
                'total_exposures': 0,
                'sequence_file': check_for_sequence_file(target_name)
            }
        targets_summary[target_name]['nights'].append(row['date_obs'])
        targets_summary[target_name]['total_exposures'] += row['num_exposures']
    
    # Display summary
    for target_name, info in sorted(targets_summary.items()):
        print(f"  {target_name} (ID: {info['target_id']})")
        print(f"    Observed on {len(info['nights'])} night(s): {', '.join(info['nights'])}")
        print(f"    Total exposures: {info['total_exposures']}")
        
        if info['sequence_file']:
            print(f"    ✓ Sequence file found: {info['sequence_file'].name}")
            print(f"      → Can be registered using mark_targets_scheduled()")
        else:
            print(f"    ✗ No sequence file found")
            print(f"      → This was likely a manual/ad-hoc observation")
        print()
    
    # Summary
    with_sequences = sum(1 for info in targets_summary.values() if info['sequence_file'])
    print("=" * 70)
    print(f"Summary: {len(targets_summary)} unique targets")
    print(f"  - {with_sequences} have sequence files (can be registered)")
    print(f"  - {len(targets_summary) - with_sequences} were ad-hoc observations")
    print("=" * 70)
    
    if with_sequences > 0:
        print("\nTo register targets with sequence files, you can:")
        print("1. Use the target_selector_gui.py to re-schedule them")
        print("2. Manually call mark_targets_scheduled() with the sequence file paths")

if __name__ == "__main__":
    main()
