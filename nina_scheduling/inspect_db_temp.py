import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'D:/scheduled_observations.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Database: {db_path}")
print(f"Tables: {[t[0] for t in tables]}")
print()

for table in tables:
    table_name = table[0]
    print(f"\n=== Table: {table_name} ===")
    schema = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    for col in schema:
        print(f"  {col[1]} ({col[2]})")
    
    count = cur.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"  Total rows: {count}")

conn.close()
