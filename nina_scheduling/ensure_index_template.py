#!/usr/bin/env python3
"""Ensure a minimal templates/index.html exists for the Flask app."""
from pathlib import Path
import sys

base = Path(__file__).resolve().parent
templates = base / 'templates'
templates.mkdir(parents=True, exist_ok=True)
index = templates / 'index.html'
if index.exists():
    print(f"Template exists: {index}")
    sys.exit(0)

content = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>nina_scheduling</title>
  <style>body{font-family:Segoe UI,Arial,sans-serif;padding:20px}</style>
</head>
<body>
  <h1>nina_scheduling web UI</h1>
  <p>This default index.html was created so the Flask app can start without template errors.</p>
  <hr>
  <h2>Recent Observations</h2>
  <p>If your `observations.sqlite` file exists, the table will be listed here by the app.</p>
</body>
</html>
"""

index.write_text(content, encoding='utf-8')
print(f"Created template: {index}")
