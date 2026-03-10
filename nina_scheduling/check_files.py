import sqlite3, pathlib

conn = sqlite3.connect('D:/scheduled_observations.sqlite')
cur = conn.cursor()
cur.execute("""
    SELECT file_path, file_name 
    FROM observations o 
    JOIN scheduled_targets st ON o.scheduled_target_id = st.scheduled_target_id 
    JOIN observation_nights n ON st.night_id = n.night_id 
    WHERE n.date_obs = '2025-12-07' 
    LIMIT 5
""")

for row in cur.fetchall():
    p = pathlib.Path(row[0])
    print(f'{row[1]}')
    print(f'  Path: {row[0]}')
    print(f'  Exists: {p.exists()}')
    print()

conn.close()
