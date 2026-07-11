"""
Generate nightly variable-star targets from NINA_API varcz_eb.db (stars table)
without scraping var.astro.cz.

This script computes upcoming minima from ephemerides in the DB, then reuses the
existing filtering/selection/export pipeline from findTargets.py.
"""

import argparse
import math
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from findTargets import (
    TIMEZONE_OFFSET,
    LATITUDE,
    LONGITUDE,
    MAX_TARGETS_PER_NIGHT,
    apply_basic_filters,
    apply_final_filters,
    apply_magnitude_filter,
    filter_targets_by_observation_night,
    parse_minima_time,
    select_targets_for_night,
    export_to_nina_format,
    export_to_nina_json,
    utc_to_local,
)

HJD_OFFSET = 2_400_000.0
DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "NINA_API" / "varcz_eb.db"


def correct_epoch(raw: Optional[float]) -> Optional[float]:
    if raw is None:
        return None
    return raw + HJD_OFFSET if raw < 2_000_000 else raw


def jd_from_datetime(dt_utc: datetime) -> float:
    return dt_utc.timestamp() / 86400.0 + 2440587.5


def datetime_from_jd(jd: float) -> datetime:
    return datetime.fromtimestamp((jd - 2440587.5) * 86400.0, tz=timezone.utc).replace(tzinfo=None)


def minima_in_window(epoch: float, period: float, jd_start: float, jd_end: float) -> List[float]:
    if epoch is None or period is None or period <= 0:
        return []
    n_lo = math.ceil((jd_start - epoch) / period)
    n_hi = math.floor((jd_end - epoch) / period)
    return [epoch + n * period for n in range(int(n_lo), int(n_hi) + 1)]


def deg_to_ra_str(ra_deg: float) -> str:
    total_seconds = ((ra_deg % 360.0) / 15.0) * 3600.0
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = total_seconds % 60.0
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def deg_to_dec_str(dec_deg: float) -> str:
    sign = "+" if dec_deg >= 0 else "-"
    a = abs(dec_deg)
    d = int(a)
    m_f = (a - d) * 60.0
    m = int(m_f)
    s = (m_f - m) * 60.0
    return f"{sign}{d:02d}:{m:02d}:{s:04.1f}"


def az_to_cardinal(az_deg: float) -> str:
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((az_deg + 22.5) // 45) % 8
    return directions[idx]


def gmst_deg(jd: float) -> float:
    return (280.46061837 + 360.98564736629 * (jd - 2451545.0)) % 360.0


def altitude_azimuth(ra_deg: float, dec_deg: float, when_utc: datetime, lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """Fast alt/az from spherical astronomy (no astropy transform per event)."""
    jd = jd_from_datetime(when_utc)
    lst = (gmst_deg(jd) + lon_deg) % 360.0
    ha_deg = (lst - ra_deg) % 360.0

    ha = math.radians(ha_deg)
    lat = math.radians(lat_deg)
    dec = math.radians(dec_deg)

    sin_alt = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(ha)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt = math.asin(sin_alt)

    cos_alt = max(1e-12, math.cos(alt))
    sin_az = -math.cos(dec) * math.sin(ha) / cos_alt
    cos_az = (math.sin(dec) - math.sin(alt) * math.sin(lat)) / (cos_alt * math.cos(lat))
    az = math.degrees(math.atan2(sin_az, cos_az)) % 360.0

    return math.degrees(alt), az


def best_name(row: sqlite3.Row) -> str:
    return row["desig_gcvs"] or row["desig_czev"] or row["name"] or f"CzeV{row['id']}"


def build_observation_window_utc(obs_date: date) -> tuple[datetime, datetime]:
    # Observation night definition used in current project: local noon -> next local noon.
    local_noon = datetime.combine(obs_date, datetime.min.time()) + timedelta(hours=12)
    start_utc = local_noon - timedelta(hours=TIMEZONE_OFFSET)
    end_utc = start_utc + timedelta(days=1)
    return start_utc, end_utc


def validate_table_name(table_name: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        raise ValueError(f"Unsafe table name: {table_name}")
    return table_name


def load_targets_from_db(db_path: Path, table_name: str, obs_date: date, lat: float, lon: float) -> List[Dict]:
    table_name = validate_table_name(table_name)
    start_utc, end_utc = build_observation_window_utc(obs_date)
    jd_start = jd_from_datetime(start_utc)
    jd_end = jd_from_datetime(end_utc)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT id, name, desig_czev, desig_gcvs, constellation, variability_type,
                   mag_max, mag_min, period_d, epoch_hjd, epoch_secondary_hjd,
                   ra_deg, dec_deg
            FROM {table_name}
            WHERE period_d IS NOT NULL
              AND period_d > 0
              AND epoch_hjd IS NOT NULL
              AND ra_deg IS NOT NULL
              AND dec_deg IS NOT NULL
            """
        ).fetchall()
    finally:
        conn.close()

    targets: List[Dict] = []

    for row in rows:
        epoch_primary = correct_epoch(row["epoch_hjd"])
        epoch_secondary = correct_epoch(row["epoch_secondary_hjd"])
        period = float(row["period_d"])

        events = []
        events.extend((jd, "I") for jd in minima_in_window(epoch_primary, period, jd_start, jd_end))
        if epoch_secondary is not None:
            events.extend((jd, "II") for jd in minima_in_window(epoch_secondary, period, jd_start, jd_end))

        for jd_value, minima_type in events:
            minima_utc = datetime_from_jd(jd_value)
            alt_deg, az_deg = altitude_azimuth(float(row["ra_deg"]), float(row["dec_deg"]), minima_utc, lat, lon)

            targets.append(
                {
                    "id": str(row["id"]),
                    "entries": "",
                    "name": best_name(row),
                    "constellation": row["constellation"] or "",
                    "minima_type": minima_type,
                    "mag_max": str(row["mag_max"] if row["mag_max"] is not None else ""),
                    "mag_min": str(row["mag_min"] if row["mag_min"] is not None else ""),
                    "band": "V",
                    "variability_type": row["variability_type"] or "",
                    "minimum_time": minima_utc.strftime("%m/%d/%y, %H:%M"),
                    "altitude": f"{alt_deg:.1f}",
                    "azimuth": az_to_cardinal(az_deg),
                    "period": str(period),
                    "ra": deg_to_ra_str(float(row["ra_deg"])),
                    "dec": deg_to_dec_str(float(row["dec_deg"])),
                }
            )

    targets.sort(key=lambda t: t["minimum_time"])
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate nightly target files from NINA_API varcz_eb.db")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to varcz_eb.db")
    parser.add_argument("--table", default="stars", help="Source table name (default: stars)")
    parser.add_argument("--obs-date", default=date.today().isoformat(), help="Observation date (YYYY-MM-DD)")
    parser.add_argument("--lat", type=float, default=LATITUDE, help="Observer latitude")
    parser.add_argument("--lon", type=float, default=LONGITUDE, help="Observer longitude")
    parser.add_argument("--telescope", default="SCT", choices=["SCT", "S50"], help="Telescope template selection")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "targets")
    parser.add_argument("--max-targets", type=int, default=MAX_TARGETS_PER_NIGHT)
    args = parser.parse_args()

    obs_date = date.fromisoformat(args.obs_date)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.db.exists():
        raise FileNotFoundError(f"Database not found: {args.db}")

    print(f"Loading ephemerides from: {args.db}")
    all_targets = load_targets_from_db(args.db, args.table, obs_date, args.lat, args.lon)
    print(f"Computed minima events in observation-night window: {len(all_targets)}")

    # Reuse existing pipeline filters for consistency with current scheduler behavior.
    filtered = apply_basic_filters(all_targets)
    filtered = filter_targets_by_observation_night(filtered, obs_date)
    filtered = apply_magnitude_filter(filtered)
    filtered = apply_final_filters(filtered)
    print(f"Targets after filters: {len(filtered)}")

    all_csv = args.output_dir / f"targets_{obs_date}.csv"
    export_to_nina_format(filtered, all_csv)

    selected = select_targets_for_night(filtered)
    selected = selected[: args.max_targets]

    if not selected and filtered:
        # Fallback: pick the earliest minima in the filtered set.
        def _minima_sort_key(target: Dict) -> datetime:
            parsed = parse_minima_time(target.get("minimum_time", ""))
            return parsed or datetime.max

        selected = sorted(filtered, key=_minima_sort_key)[: args.max_targets]
        for target in selected:
            minima_utc = parse_minima_time(target.get("minimum_time", ""))
            if minima_utc:
                target["minima_datetime_utc"] = minima_utc
                target["minima_datetime_local"] = utc_to_local(minima_utc)

    print(f"Selected nightly targets: {len(selected)}")

    if selected:
        selected_csv = args.output_dir / f"selected_targets_{obs_date}.csv"
        export_to_nina_format(selected, selected_csv)
        export_to_nina_json(selected, output_dir=args.output_dir, telescope=args.telescope)
        print(f"Wrote files to: {args.output_dir}")
    else:
        print("No suitable selected targets for this night")


if __name__ == "__main__":
    main()
