#!/usr/bin/env python3
"""
Demonstration of NINA scheduling database integration.

This script shows how scheduled targets and observed exposures are linked together
through the proper foreign key chain.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add logexploit to path
sys.path.insert(0, str(Path(__file__).parent.parent / "logexploit" / "src"))

from logexploit.database import mark_targets_scheduled


def print_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_table(cursor, title):
    """Print query results as a formatted table."""
    print(f"\n{title}:")
    print("-" * 70)
    
    rows = cursor.fetchall()
    if not rows:
        print("  (No results)")
        return
    
    # Print column headers
    headers = [desc[0] for desc in cursor.description]
    print("  " + " | ".join(f"{h:20s}" for h in headers))
    print("  " + "-" * (23 * len(headers)))
    
    # Print rows
    for row in rows:
        print("  " + " | ".join(f"{str(v):20s}" for v in row))


def demo_integration(db_path="observations_demo.sqlite"):
    """Demonstrate the complete integration workflow."""
    
    db_path = Path(__file__).parent / db_path
    
    # Clean slate
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing demo database: {db_path}")
    
    print_header("NINA SCHEDULING DATABASE INTEGRATION DEMO")
    print(f"Database: {db_path}\n")
    
    # Initialize database with schema
    print("📋 Initializing database schema...")
    conn = sqlite3.connect(db_path)
    schema_path = Path(__file__).parent / "schema.sql"
    
    with open(schema_path) as f:
        conn.executescript(f.read())
    
    print("✅ Schema created\n")
    
    # =========================================================================
    # STEP 1: SCHEDULING (what findTargets.py does)
    # =========================================================================
    
    print_header("STEP 1: SCHEDULE TARGETS (Before Observing)")
    
    observation_date = "2025-12-08"
    telescope = "SCT 8-inch"
    
    # Targets we want to observe tonight
    targets_to_schedule = [
        {
            'name': 'EG Scl',
            'ra': '23:38:15.2',
            'dec': '-40:38:27',
            'constellation': 'Scl',
            'magnitude_max': 7.8,
            'magnitude_min': 8.5,
            'variability_type': 'EA'
        },
        {
            'name': 'V* BV Cet',
            'ra': '02:46:12.4',
            'dec': '-11:52:03',
            'constellation': 'Cet',
            'magnitude_max': 11.2,
            'magnitude_min': 12.1,
            'variability_type': 'EB'
        },
        {
            'name': 'HX Eri',
            'ra': '03:28:45.1',
            'dec': '-09:12:34',
            'constellation': 'Eri',
            'magnitude_max': 10.5,
            'magnitude_min': 11.3,
            'variability_type': 'EA'
        }
    ]
    
    print(f"Scheduling {len(targets_to_schedule)} targets for {observation_date}...")
    print(f"Telescope: {telescope}\n")
    
    for target in targets_to_schedule:
        print(f"  - {target['name']} ({target['variability_type']}, mag {target['magnitude_max']}-{target['magnitude_min']})")
    
    # Call mark_targets_scheduled (this is what findTargets.py calls)
    scheduled_count = mark_targets_scheduled(
        db_path=db_path,
        targets=targets_to_schedule,
        observation_date=observation_date,
        telescope=telescope
    )
    
    print(f"\n✅ Scheduled {scheduled_count} targets\n")
    
    # Show what was created
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM observation_nights")
    print_table(cursor, "📅 observation_nights table")
    
    cursor.execute("""
        SELECT target_id, target_name, constellation, 
               COALESCE(magnitude_max, 0) as mag_max,
               COALESCE(magnitude_min, 0) as mag_min,
               variability_type
        FROM targets
    """)
    print_table(cursor, "🎯 targets table")
    
    cursor.execute("""
        SELECT st.scheduled_target_id, st.night_id, st.target_id, 
               t.target_name, st.status
        FROM scheduled_targets st
        JOIN targets t ON st.target_id = t.target_id
    """)
    print_table(cursor, "📋 scheduled_targets table (THE SCHEDULING RECORDS)")
    
    # =========================================================================
    # STEP 2: SIMULATE OBSERVATIONS (what would be in NINA log)
    # =========================================================================
    
    print_header("STEP 2: SIMULATE OBSERVATIONS (NINA creates log)")
    
    print("🔭 Observing session in progress...")
    print("   (In reality, NINA would create a log file with exposure records)")
    print("\nSimulating exposures being taken:\n")
    
    # Simulate some observations - we observed 2 out of 3 targets
    simulated_exposures = [
        # EG Scl - we got this one
        {
            'target_name': 'EG Scl',
            'file_path': r'C:\Users\aegis\Documents\N.I.N.A\2025-12-08\LIGHT\EG Scl\2025-12-08_20-30-15_V_-10.2_120.0s_0001.fits',
            'exposure_time': 120.0,
            'filter': 'V',
            'datetime': '2025-12-08 20:30:15'
        },
        {
            'target_name': 'EG Scl',
            'file_path': r'C:\Users\aegis\Documents\N.I.N.A\2025-12-08\LIGHT\EG Scl\2025-12-08_20-32-17_V_-10.2_120.0s_0002.fits',
            'exposure_time': 120.0,
            'filter': 'V',
            'datetime': '2025-12-08 20:32:17'
        },
        {
            'target_name': 'EG Scl',
            'file_path': r'C:\Users\aegis\Documents\N.I.N.A\2025-12-08\LIGHT\EG Scl\2025-12-08_20-34-19_B_-10.2_180.0s_0003.fits',
            'exposure_time': 180.0,
            'filter': 'B',
            'datetime': '2025-12-08 20:34:19'
        },
        # HX Eri - we got this one too
        {
            'target_name': 'HX Eri',
            'file_path': r'C:\Users\aegis\Documents\N.I.N.A\2025-12-08\LIGHT\HX Eri\2025-12-08_21-15-30_V_-10.1_150.0s_0001.fits',
            'exposure_time': 150.0,
            'filter': 'V',
            'datetime': '2025-12-08 21:15:30'
        },
        {
            'target_name': 'HX Eri',
            'file_path': r'C:\Users\aegis\Documents\N.I.N.A\2025-12-08\LIGHT\HX Eri\2025-12-08_21-18-02_V_-10.1_150.0s_0002.fits',
            'exposure_time': 150.0,
            'filter': 'V',
            'datetime': '2025-12-08 21:18:02'
        },
        # BV Cet - NOT observed (clouded out)
    ]
    
    for exp in simulated_exposures:
        print(f"  📸 {exp['target_name']}: {exp['filter']} {exp['exposure_time']}s @ {exp['datetime']}")
    
    print(f"\n✅ {len(simulated_exposures)} exposures taken")
    print("⚠️  Note: V* BV Cet was scheduled but NOT observed (weather?)")
    
    # =========================================================================
    # STEP 3: IMPORT OBSERVATIONS (what logexploit --nina-integration does)
    # =========================================================================
    
    print_header("STEP 3: IMPORT & LINK OBSERVATIONS")
    
    print("🔗 Linking observed exposures to scheduled targets...")
    print("   (This is what happens when you run: logexploit --nina-integration)\n")
    
    # Get the night_id
    cursor.execute("SELECT night_id FROM observation_nights WHERE date_obs = ?", (observation_date,))
    night_id = cursor.fetchone()[0]
    
    linked_count = 0
    
    for exp in simulated_exposures:
        # Find the target
        cursor.execute("SELECT target_id FROM targets WHERE target_name = ?", (exp['target_name'],))
        target_row = cursor.fetchone()
        if not target_row:
            print(f"  ❌ Target not found: {exp['target_name']}")
            continue
        
        target_id = target_row[0]
        
        # Find the scheduled_target (THIS IS THE KEY LINK!)
        cursor.execute("""
            SELECT scheduled_target_id FROM scheduled_targets
            WHERE night_id = ? AND target_id = ?
        """, (night_id, target_id))
        
        scheduled_target_row = cursor.fetchone()
        if not scheduled_target_row:
            print(f"  ⚠️  No scheduled entry for {exp['target_name']} - creating 'unscheduled' entry")
            cursor.execute("""
                INSERT INTO scheduled_targets (night_id, target_id, status)
                VALUES (?, ?, 'unscheduled')
            """, (night_id, target_id))
            scheduled_target_id = cursor.lastrowid
        else:
            scheduled_target_id = scheduled_target_row[0]
            # Update status to completed
            cursor.execute("""
                UPDATE scheduled_targets 
                SET status = 'completed'
                WHERE scheduled_target_id = ?
            """, (scheduled_target_id,))
        
        # Store the observation with FK to scheduled_target
        cursor.execute("""
            INSERT INTO observations (
                scheduled_target_id, file_path, file_name,
                exposure_time_sec, filter_name, datetime_start
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            scheduled_target_id,
            exp['file_path'],
            Path(exp['file_path']).name,
            exp['exposure_time'],
            exp['filter'],
            exp['datetime']
        ))
        
        print(f"  ✅ Linked: {exp['target_name']} → scheduled_target_id={scheduled_target_id}")
        linked_count += 1
    
    conn.commit()
    print(f"\n✅ Linked {linked_count} exposures to scheduled targets\n")
    
    # =========================================================================
    # STEP 4: QUERY THE INTEGRATED DATA
    # =========================================================================
    
    print_header("STEP 4: QUERY SCHEDULED vs. OBSERVED")
    
    # Show the final integrated view
    cursor.execute("""
        SELECT 
            st.scheduled_target_id,
            t.target_name,
            st.status,
            COUNT(o.observation_id) AS exposure_count,
            GROUP_CONCAT(DISTINCT o.filter_name) AS filters,
            COALESCE(SUM(o.exposure_time_sec), 0) AS total_time_sec
        FROM scheduled_targets st
        JOIN targets t ON st.target_id = t.target_id
        LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
        WHERE st.night_id = ?
        GROUP BY st.scheduled_target_id, t.target_name, st.status
        ORDER BY t.target_name
    """, (night_id,))
    
    print_table(cursor, "📊 INTEGRATED VIEW: Scheduled vs. Observed")
    
    # Show individual exposures
    cursor.execute("""
        SELECT 
            t.target_name,
            o.filter_name,
            o.exposure_time_sec,
            o.datetime_start,
            o.file_name
        FROM observations o
        JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id
        JOIN targets t ON st.target_id = t.target_id
        ORDER BY o.datetime_start
    """)
    
    print_table(cursor, "📸 Individual Exposures (with FK links)")
    
    # =========================================================================
    # ANALYSIS QUERIES
    # =========================================================================
    
    print_header("BONUS: ANALYSIS QUERIES")
    
    # What was scheduled but not observed?
    cursor.execute("""
        SELECT 
            t.target_name,
            st.status,
            'NOT OBSERVED' as note
        FROM scheduled_targets st
        JOIN targets t ON st.target_id = t.target_id
        LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
        WHERE st.night_id = ?
          AND o.observation_id IS NULL
    """, (night_id,))
    
    print_table(cursor, "❌ Scheduled but NOT Observed")
    
    # Completion rate
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT st.target_id) AS total_scheduled,
            COUNT(DISTINCT CASE WHEN o.observation_id IS NOT NULL THEN st.target_id END) AS observed,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN o.observation_id IS NOT NULL THEN st.target_id END) / 
                  COUNT(DISTINCT st.target_id), 1) AS completion_rate
        FROM scheduled_targets st
        LEFT JOIN observations o ON st.scheduled_target_id = o.scheduled_target_id
        WHERE st.night_id = ?
    """, (night_id,))
    
    print_table(cursor, "📈 Completion Statistics")
    
    conn.close()
    
    print_header("DEMO COMPLETE")
    print(f"Demo database saved at: {db_path}")
    print("\nYou can explore it with:")
    print(f"  sqlite3 {db_path}")
    print("\nKey takeaway:")
    print("  The FK chain: observation_nights → targets → scheduled_targets → observations")
    print("  Links what you PLANNED to observe with what you ACTUALLY observed!\n")


if __name__ == "__main__":
    demo_integration()
