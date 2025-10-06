from flask import Flask, render_template, request, redirect, url_for, flash
from pathlib import Path
import subprocess
import sqlite3
import os
import shlex

app = Flask(__name__)
app.secret_key = 'replace-this-with-a-better-secret'

DB_PATH = Path(__file__).parent / 'observations.sqlite'


def get_db_rows(limit=200, search=None):
    if not DB_PATH.exists():
        return []
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()
    # Build query; allow optional search on target (case-insensitive)
    q = 'SELECT id,target,dateobs,telescope,processed FROM observations'
    params = []
    if search:
        # Use SQLite COLLATE NOCASE to make the LIKE comparison case-insensitive
        q += ' WHERE target LIKE ? COLLATE NOCASE'
        params.append(f"%{search}%")
    q += f' ORDER BY dateobs DESC LIMIT {int(limit)}'
    rows = cur.execute(q, params).fetchall()
    con.close()
    return rows


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mode = request.form.get('mode', 'light')
        base_path = request.form.get('base_path', 'D:\\')
        seestar_path = request.form.get('seestar_path', 'D:\\Seestar')
        dry_run = 'dry_run' in request.form
        # Build command
        cmd = ['python', 'data_scan.py', '--mode', mode, '--base-path', base_path, '--seestar-path', seestar_path]
        if dry_run:
            cmd.append('--dry-run')
        # Run subprocess in nina_scheduling dir
        try:
            proc = subprocess.run(cmd, cwd=os.path.dirname(__file__), capture_output=True, text=True, check=False)
            flash('Command finished. Return code: %s' % proc.returncode)
            flash(proc.stdout)
            if proc.stderr:
                flash(proc.stderr)
        except Exception as e:
            flash('Failed to run scanner: %s' % e)
        return redirect(url_for('index'))

    # handle search from query string
    q = request.args.get('q', '').strip() if request.args else ''
    rows = get_db_rows(search=q)
    return render_template('index.html', rows=rows, q=q)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
