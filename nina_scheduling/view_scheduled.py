#!/usr/bin/env python3
"""Quick script to view scheduled targets in the database"""

import sqlite3
from datetime import date

db_path = "Z:/scheduled_observations.sqlite"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Get tonight's observation night
tonight = date.today()
cursor = conn.cursor()

print(f"\n=== Observation Night for {tonight} ===")
cursor.execute("""
    SELECT night_id, date_obs, telescope, dark_sky_start, dark_sky_end
    FROM observation_nights
    WHERE date_obs = ?
""", (str(tonight),))

night = cursor.fetchone()
if night:
    print(f"Night ID: {night['night_id']}")
    print(f"Date: {night['date_obs']}")
    print(f"Telescope: {night['telescope']}")
    print(f"Dark sky: {night['dark_sky_start']} to {night['dark_sky_end']}")
    
    # Get scheduled targets for this night
    print(f"\n=== Scheduled Targets ===")
    cursor.execute("""
        SELECT st.scheduled_target_id, st.target_id, st.sequence_id,
               st.scheduled_start_time, st.scheduled_end_time, st.status,
               st.images_captured, st.completion_percentage,
               t.target_name, t.ra_hours, t.ra_minutes, t.ra_seconds,
               t.dec_degrees, t.dec_minutes, t.dec_seconds, t.dec_negative,
               t.magnitude_max, t.magnitude_min,
               s.sequence_name
        FROM scheduled_targets st
        LEFT JOIN targets t ON st.target_id = t.target_id
        LEFT JOIN sequences s ON st.sequence_id = s.sequence_id
        WHERE st.night_id = ?
        ORDER BY st.scheduled_start_time
    """, (night['night_id'],))
    
    for i, target in enumerate(cursor.fetchall(), 1):
        print(f"\n{i}. {target['target_name']}")
        print(f"   Scheduled Target ID: {target['scheduled_target_id']}")
        print(f"   Sequence: {target['sequence_name']}")
        print(f"   Time: {target['scheduled_start_time']} to {target['scheduled_end_time']}")
        print(f"   Status: {target['status']}")
        if target['ra_hours'] is not None:
            ra_str = f"{target['ra_hours']}h {target['ra_minutes']}m {target['ra_seconds']:.1f}s"
            dec_sign = '-' if target['dec_negative'] else '+'
            dec_str = f"{dec_sign}{abs(target['dec_degrees'])}° {target['dec_minutes']}' {target['dec_seconds']:.1f}\""
            print(f"   Coordinates: RA {ra_str}, Dec {dec_str}")
            if target['magnitude_max']:
                print(f"   Magnitude: {target['magnitude_min']:.1f} - {target['magnitude_max']:.1f}")
else:
    print(f"No observation night found for {tonight}")

conn.close()
