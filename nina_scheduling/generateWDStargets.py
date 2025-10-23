#!/usr/bin/env python3
"""
Query the local WDS SQLite database using numeric filters provided in a
parameter file `ds_parameters.txt`.

The script will prefer the numeric table `wds_deg` if it exists (fast numeric queries).
If not present, it will scan the `wds` table in chunks and parse DEJ2000 strings to numeric deg.

Outputs a TSV file with matching rows (configurable in parameters).
"""
__doc__ += """

Usage example:
    python query_wds_by_params.py

To search the WDS table and output 10 targets, set the following in ds_parameters.txt:
    export_limit = 10
    write_output = True

This will write the results to the output_tsv file specified in ds_parameters.txt (default: wds_ds_results.tsv).
"""

import sqlite3
import os
from pathlib import Path
import pandas as pd
import math
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_sun
import astropy.units as u
import json
from copy import deepcopy

# exposure time utility
from exposure_time import get_exposure_time

CONFIG_PATH = 'ds_parameters.txt'


def load_params(path: str) -> dict:
    params = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                # Remove inline comments after value
                if '#' in v:
                    v = v.split('#', 1)[0].strip()
                # try to convert to int/float, fallback to string
                try:
                    if v == '':
                        params[k] = v
                    elif '.' in v:
                        params[k] = float(v)
                    else:
                        params[k] = int(v)
                except ValueError:
                    # handle booleans
                    low = v.lower()
                    if low in ('true', 'yes', '1'):
                        params[k] = True
                    elif low in ('false', 'no', '0'):
                        params[k] = False
                    else:
                        params[k] = v
    return params


def parse_dec_to_deg(dec_str: str) -> float:
    """
    Parse declination string in format 'DD MM SS.SS' to decimal degrees.
    Handles negative declination correctly.
    
    Examples:
    '+42 30 15.5' -> +42.5043
    '-15 30 45.0' -> -15.5125
    """
    try:
        parts = dec_str.strip().split()
        d = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        
        # Convert minutes and seconds to decimal degrees
        decimal_offset = m/60.0 + s/3600.0
        
        # Handle negative declination
        if dec_str.strip().startswith('-') or d < 0:
            # For negative declination, subtract the minutes/seconds portion
            return d - decimal_offset
        else:
            # For positive declination, add the minutes/seconds portion
            return d + decimal_offset
    except Exception:
        return float('nan')


def query_using_wds_deg(conn: sqlite3.Connection, params: dict, scheduled_column_present: bool) -> pd.DataFrame:
        q = f"""
        SELECT * FROM wds_deg
        WHERE Dec_deg BETWEEN {params['dej2000_min']} AND {params['dej2000_max']}
            AND Obs2 < {params['obs2_before']}
            AND sep2 BETWEEN {params['sep_min']} AND {params['sep_max']}
            AND mag1 BETWEEN {params['mag1_min']} AND {params['mag1_max']}
            AND mag2 BETWEEN {params['mag2_min']} AND {params['mag2_max']}
        """
        # If the scheduled column exists, only select rows where it is NULL or empty
        if scheduled_column_present:
                q += "\n      AND (scheduled IS NULL OR scheduled = '')"
        print('Executing numeric query on wds_deg...')
        return pd.read_sql_query(q, conn)


def scan_wds_table(conn: sqlite3.Connection, params: dict, chunk_size: int = 20000, scheduled_column_present: bool = False) -> pd.DataFrame:
    print('wds_deg not found; scanning wds table in chunks and parsing DEJ2000...')
    offset = 0
    dfs = []
    while True:
        df = pd.read_sql_query(f"SELECT * FROM wds LIMIT {chunk_size} OFFSET {offset}", conn)
        if df.empty:
            break
        # parse DEJ2000 to numeric deg
        df['Dec_deg'] = df['DEJ2000'].fillna('').apply(parse_dec_to_deg)
        # perform filters
        mask = (
            (df['Dec_deg'] >= params['dej2000_min']) &
            (df['Dec_deg'] <= params['dej2000_max']) &
            (pd.to_numeric(df['Obs2'], errors='coerce') < params['obs2_before']) &
            (pd.to_numeric(df['sep2'], errors='coerce') >= params['sep_min']) &
            (pd.to_numeric(df['sep2'], errors='coerce') <= params['sep_max']) &
            (pd.to_numeric(df['mag1'], errors='coerce') >= params['mag1_min']) &
            (pd.to_numeric(df['mag1'], errors='coerce') <= params['mag1_max']) &
            (pd.to_numeric(df['mag2'], errors='coerce') >= params['mag2_min']) &
            (pd.to_numeric(df['mag2'], errors='coerce') <= params['mag2_max'])
        )
        # If scheduled column exists, filter out rows where scheduled is not NULL/empty
        if scheduled_column_present and 'scheduled' in df.columns:
            mask = mask & (df['scheduled'].isna() | (df['scheduled'] == ''))
        matched = df[mask]
        if not matched.empty:
            dfs.append(matched)
        print(f'Processed offset {offset}, rows read {len(df)}, matched {len(matched)}')
        offset += len(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    if not Path(CONFIG_PATH).exists():
        print(f"Config file '{CONFIG_PATH}' not found")
        return
    params = load_params(CONFIG_PATH)
    db_path = params.get('db_path', 'wds_catalog.sqlite')
    chunk_size = int(params.get('chunk_size', 20000))
    out_tsv = params.get('output_tsv', 'wds_ds_results.tsv')
    export_limit = int(params.get('export_limit', 0))
    # If write_output is True, the script will write TSV. Default is False (keep in memory).
    write_output = params.get('write_output', False)

    if not Path(db_path).exists():
        print(f"Database '{db_path}' not found")
        return

    conn = sqlite3.connect(db_path)
    # check if wds_deg exists
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wds_deg'")
    wds_deg_exists = bool(cur.fetchone())
    # detect whether scheduled column exists in wds (or wds_deg)
    scheduled_column_present = False
    try:
        cur.execute("PRAGMA table_info(wds)")
        cols = [r[1] for r in cur.fetchall()]
        scheduled_column_present = 'scheduled' in cols
    except Exception:
        scheduled_column_present = False

    if wds_deg_exists:
        df = query_using_wds_deg(conn, params, scheduled_column_present)
    else:
        df = scan_wds_table(conn, params, chunk_size=chunk_size, scheduled_column_present=scheduled_column_present)

    conn.close()

    if df.empty:
        print('No matches found')
        return

    print(f'Found {len(df)} matching rows')
    if export_limit > 0:
        df = df.head(export_limit)

    # Keep the DataFrame in memory. Only write to disk if explicitly requested.
    if write_output:
        df.to_csv(out_tsv, sep='\t', index=False)
        print('Exported to', out_tsv)
    else:
        print('write_output is False: results retained in memory (not written to disk).')
        # Print a quick sample for convenience
        with pd.option_context('display.max_rows', 10, 'display.max_columns', 12):
            print(df.head(10))

    # If this module is imported, callers can access the DataFrame via the `last_query_df` global.
    global last_query_df
    last_query_df = df

    # --- New: select targets relative to astronomical twilight ---
    # Load selection params
    obs_lat = float(params.get('observer_latitude', -34.9285))
    obs_lon = float(params.get('observer_longitude', 138.6007))
    obs_height = float(params.get('observer_elevation', 50))
    n_targets = int(params.get('n_targets', 3))
    t_step_hours = float(params.get('t_step_hours', 1.0))
    twilight_type = str(params.get('twilight_type', 'evening')).lower()

    # Compute astronomical twilight time (evening or morning) for current date
    location = EarthLocation(lat=obs_lat*u.deg, lon=obs_lon*u.deg, height=obs_height*u.m)
    now = Time.now()
    date_str = now.to_value('iso', subfmt='date')
    # search times around local midnight +/- 12h
    midnight = Time(date_str + 'T00:00:00')
    times = midnight + (range(-24, 25, 1) * u.hour)

    # compute sun altitudes
    sun_altaz = get_sun(times).transform_to(AltAz(obstime=times, location=location)).alt
    # astronomical twilight is sun altitude = -18 deg
    # find index where sun crosses -18 deg in evening (sun altitude decreasing past -18)
    tw_idx = None
    if twilight_type.startswith('even'):
        # look for last time before midnight where sun altitude > -18 then next is <= -18
        for i in range(len(times)-1):
            if sun_altaz[i] > -18*u.deg and sun_altaz[i+1] <= -18*u.deg:
                tw_idx = i+1
        if tw_idx is None:
            tw_idx = next((i for i in range(len(times)-1) if sun_altaz[i] > -18*u.deg and sun_altaz[i+1] <= -18*u.deg), len(times)//2)
    else:
        # morning twilight: find first time after midnight where altitude crosses -18 upward
        for i in range(len(times)-1):
            if sun_altaz[i] <= -18*u.deg and sun_altaz[i+1] > -18*u.deg:
                tw_idx = i+1
        if tw_idx is None:
            tw_idx = next((i for i in range(len(times)-1) if sun_altaz[i] <= -18*u.deg and sun_altaz[i+1] > -18*u.deg), len(times)//2)

    twilight_time = times[tw_idx]
    print('Twilight (astronomical) time found:', twilight_time.iso)

    # Convert twilight time to Local Sidereal Time (LST) in hours
    lst = twilight_time.sidereal_time('mean', longitude=obs_lon*u.deg)
    # Convert Angle to decimal hours using hourangle units
    lst_hours = lst.to(u.hourangle).value
    print(f'Local Sidereal Time at twilight: {lst_hours:.3f} h')

    # Convert RAJ2000 strings to decimal hours for comparison
    def ra_to_hours(ra_str):
        try:
            parts = ra_str.strip().split()
            h = float(parts[0]); m = float(parts[1]); s = float(parts[2])
            return h + m/60.0 + s/3600.0
        except Exception:
            return float('nan')

    df['RA_hours'] = df['RAJ2000'].fillna('').apply(ra_to_hours)

    # compute difference in hours, taking wrap-around into account
    def hour_diff(a, b):
        d = a - b
        d = (d + 12) % 24 - 12
        return abs(d)

    # find the row with RA closest to LST
    df_valid = df.dropna(subset=['RA_hours'])
    df_valid['delta_h'] = df_valid['RA_hours'].apply(lambda r: hour_diff(r, lst_hours))
    df_valid = df_valid.sort_values('delta_h')

    selected = []
    if not df_valid.empty:
        # pick the closest as base
        base = df_valid.iloc[0]
        selected.append(base)
        base_ra = base['RA_hours']
        # select additional targets incremented by t_step_hours
        for i in range(1, n_targets):
            target_ra = (base_ra + i * t_step_hours) % 24
            # find closest to target_ra
            df_valid['delta_target'] = df_valid['RA_hours'].apply(lambda r: hour_diff(r, target_ra))
            row = df_valid.sort_values('delta_target').iloc[0]
            selected.append(row)

    print('\nSelected targets:')
    for i, row in enumerate(selected, 1):
        print(f"{i}. WDS {row['WDS']} ({row.get('Disc','')}) RA={row['RAJ2000']} Dec={row['DEJ2000']} RA_h={row['RA_hours']:.3f}")

    # store selected in global
    global last_selected_targets
    last_selected_targets = pd.DataFrame(selected)

    # --- Write N.I.N.A. target files for selected targets ---
    def write_nina_targets(selected_df, template_path='Double_Star.template.json', out_dir='WDS_targets'):
        # Create date-stamped subdirectory
        from datetime import datetime
        date_stamp = datetime.now().strftime('%Y%m%d')
        dated_out_dir = os.path.join(out_dir, date_stamp)
        
        # Load template once
        with open(template_path, 'r') as tf:
            template = json.load(tf)

        os.makedirs(dated_out_dir, exist_ok=True)

        def parse_ra(ra_str):
            parts = ra_str.strip().split()
            h = int(float(parts[0])); m = int(float(parts[1])); s = float(parts[2])
            return h, m, s

        def parse_dec(dec_str):
            parts = dec_str.strip().split()
            d = int(float(parts[0])); m = int(float(parts[1])); s = float(parts[2])
            neg = dec_str.strip().startswith('-') or d < 0
            
            # N.I.N.A expects DecDegrees to be negative when NegativeDec is true
            # Special case: preserve -0.0 for "-00" declinations
            if neg and d == 0:
                return neg, -0.0, m, s
            
            return neg, d, m, s

        # helper to set the TakeExposure ExposureTime value inside template recursively
        def set_take_exposure_time(obj, exposure_seconds):
            if isinstance(obj, dict):
                # detect take exposure items by $type containing 'TakeExposure'
                t = obj.get('$type', '')
                if 'TakeExposure' in t:
                    obj['ExposureTime'] = float(exposure_seconds)
                for k, v in obj.items():
                    set_take_exposure_time(v, exposure_seconds)
            elif isinstance(obj, list):
                for item in obj:
                    set_take_exposure_time(item, exposure_seconds)

        # Ensure DB has scheduled and processed columns; open a connection for updates
        db_conn = None
        try:
            db_conn = sqlite3.connect(db_path)
            cur = db_conn.cursor()
            cur.execute("PRAGMA table_info(wds)")
            cols = [r[1] for r in cur.fetchall()]
            if 'scheduled' not in cols:
                try:
                    cur.execute("ALTER TABLE wds ADD COLUMN scheduled TEXT")
                    db_conn.commit()
                except Exception:
                    pass
            if 'processed' not in cols:
                try:
                    cur.execute("ALTER TABLE wds ADD COLUMN processed INTEGER DEFAULT 0")
                    db_conn.commit()
                except Exception:
                    pass
        except Exception as e:
            print('Warning: could not ensure scheduled/processed columns in DB:', e)

        created_files = []
        for idx, row in selected_df.iterrows():
            # row may be a Series or dict-like
            disc = str(row.get('Disc', 'UNK')).strip()
            wds_id = str(row.get('WDS', '')).replace(' ', '')
            ra_str = str(row.get('RAJ2000', '00 00 00'))
            dec_str = str(row.get('DEJ2000', '+00 00 00'))
            mag1 = row.get('mag1', None)
            if mag1 is None or (isinstance(mag1, float) and math.isnan(mag1)):
                mag1 = float(row.get('mag1', 10.0))

            exposure = get_exposure_time(float(mag1))

            # deep copy template
            tjson = deepcopy(template)

            # Update target name and coordinates
            # Format target name as: WDSID (Disc)
            target_name = f"{wds_id} ({disc})"
            tjson['Target']['TargetName'] = target_name

            # RA
            ra_h, ra_m, ra_s = parse_ra(ra_str)
            tjson['Target']['InputCoordinates']['RAHours'] = int(ra_h)
            tjson['Target']['InputCoordinates']['RAMinutes'] = int(ra_m)
            tjson['Target']['InputCoordinates']['RASeconds'] = float(ra_s)

            # Dec
            neg, dec_d, dec_m, dec_s = parse_dec(dec_str)
            tjson['Target']['InputCoordinates']['NegativeDec'] = bool(neg)
            tjson['Target']['InputCoordinates']['DecDegrees'] = int(dec_d)
            tjson['Target']['InputCoordinates']['DecMinutes'] = int(dec_m)
            tjson['Target']['InputCoordinates']['DecSeconds'] = float(dec_s)

            # Update exposure time in template
            set_take_exposure_time(tjson, exposure)

            # Write out using WDSID (Disc) in filename, sanitized for filesystem
            # Do not include exposure in the filename per user request
            raw_name = f"{wds_id} ({disc}).json"
            # Replace characters invalid in Windows filenames
            invalid_chars = '<>:"/\\|?*'
            filename = ''.join(c if c not in invalid_chars else '_' for c in raw_name)
            # Also collapse multiple spaces
            filename = '_'.join(filename.split())
            out_path = os.path.join(dated_out_dir, filename)
            with open(out_path, 'w') as out_f:
                json.dump(tjson, out_f, indent=2)
            created_files.append(out_path)

            # Update DB scheduled and processed fields for this WDS id
            try:
                if db_conn:
                    today = Time.now().to_value('iso', subfmt='date')
                    cur.execute("UPDATE wds SET scheduled = ?, processed = ? WHERE WDS = ?", (today, 0, wds_id))
                    db_conn.commit()
            except Exception as e:
                print(f"Warning: could not update DB for {wds_id}: {e}")

        # close db_conn if opened
        try:
            if db_conn:
                db_conn.close()
        except Exception:
            pass

        return created_files

    # Only write NINA files if user requested via param 'write_nina'
    if params.get('write_nina', False):
        created = write_nina_targets(last_selected_targets)
        print('\nCreated N.I.N.A. target files:')
        for p in created:
            print(' -', p)


if __name__ == '__main__':
    main()
