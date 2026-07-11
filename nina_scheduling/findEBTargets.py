"""
Find eclipsing binary targets from the NINA_API varcz_eb database.

Rules enforced:
- Target must be eclipsing binary (variability type begins with 'E').
- Event must be a primary (I) or secondary (II) minimum during the observation night.
- Event azimuth at minimum must be within the configured azimuth range.
"""

import argparse
import csv
import json
import math
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

HJD_OFFSET = 2_400_000.0
DEFAULT_DB_PATH = (Path(__file__).resolve().parent / ".." / ".." / "NINA_API" / "varcz_eb.db").resolve()
DEFAULT_TABLE = "stars"

SECTOR_BOUNDS = {
    "N": (337.5, 22.5),
    "NE": (22.5, 67.5),
    "E": (67.5, 112.5),
    "SE": (112.5, 157.5),
    "S": (157.5, 202.5),
    "SW": (202.5, 247.5),
    "W": (247.5, 292.5),
    "NW": (292.5, 337.5),
}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_defaults() -> Dict[str, float]:
    try:
        from config import get_flat_config

        cfg = get_flat_config()
        return {
            "latitude": float(cfg["LATITUDE"]),
            "longitude": float(cfg["LONGITUDE"]),
            "timezone_offset": float(cfg["TIMEZONE_OFFSET"]),
        }
    except Exception:
        return {
            "latitude": -35.0,
            "longitude": 149.08,
            "timezone_offset": 10.0,
        }


def _safe_table_name(table_name: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        raise ValueError(f"Unsafe table name: {table_name}")
    return table_name


def resolve_db_path(db_path: Path) -> Path:
    """Resolve DB path with helpful fallbacks for common launch locations."""
    script_dir = Path(__file__).resolve().parent
    candidates: List[Path] = []

    if db_path.is_absolute():
        candidates.append(db_path)
    else:
        candidates.append(Path.cwd() / db_path)
        candidates.append(script_dir / db_path)
        # Common project layout fallback: ..\..\NINA_API\<db_name>
        candidates.append((script_dir / ".." / ".." / "NINA_API" / db_path.name).resolve())

    # Always try the project default as a final fallback.
    if DEFAULT_DB_PATH not in candidates:
        candidates.append(DEFAULT_DB_PATH)

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    searched = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        f"Database not found for input '{db_path}'. Searched:\n{searched}"
    )


def _to_jd(utc_dt: datetime) -> float:
    return utc_dt.timestamp() / 86400.0 + 2440587.5


def _from_jd(jd_value: float) -> datetime:
    return datetime.fromtimestamp((jd_value - 2440587.5) * 86400.0, tz=timezone.utc).replace(tzinfo=None)


def ra_deg_to_sexagesimal(ra_deg: float) -> str:
    total_seconds = ((ra_deg % 360.0) / 15.0) * 3600.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60.0
    return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"


def dec_deg_to_sexagesimal(dec_deg: float) -> str:
    sign = "+" if dec_deg >= 0 else "-"
    abs_deg = abs(dec_deg)
    degrees = int(abs_deg)
    minutes_float = (abs_deg - degrees) * 60.0
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60.0
    return f"{sign}{degrees:02d}:{minutes:02d}:{seconds:04.1f}"


def _correct_epoch(raw_epoch: Optional[float]) -> Optional[float]:
    if raw_epoch is None:
        return None
    return raw_epoch + HJD_OFFSET if raw_epoch < 2_000_000 else raw_epoch


def _night_window_utc(observation_date: date, timezone_offset: float) -> tuple[datetime, datetime]:
    local_noon = datetime.combine(observation_date, datetime.min.time()) + timedelta(hours=12)
    start_utc = local_noon - timedelta(hours=timezone_offset)
    end_utc = start_utc + timedelta(days=1)
    return start_utc, end_utc


def get_dark_night_bounds_local(observation_date: date, latitude: float, longitude: float) -> tuple[datetime, datetime]:
    """Return dark-sky start and astronomical dawn in local time."""
    try:
        from findTargets import calculate_astronomical_dawn, calculate_sunset_time

        dark_sky = calculate_sunset_time(observation_date, latitude, longitude, sun_altitude=-15.0)
        dawn = calculate_astronomical_dawn(observation_date, latitude, longitude)

        night_start = datetime.combine(observation_date, datetime.strptime(dark_sky, "%H:%M").time())
        night_end = datetime.combine(observation_date + timedelta(days=1), datetime.strptime(dawn, "%H:%M").time())
        return night_start, night_end
    except Exception:
        # Fallback bounds if astronomical helpers are unavailable.
        night_start = datetime.combine(observation_date, datetime.strptime("18:00", "%H:%M").time())
        night_end = datetime.combine(observation_date + timedelta(days=1), datetime.strptime("06:00", "%H:%M").time())
        return night_start, night_end


def _minima_jd_in_window(epoch_jd: Optional[float], period_days: float, jd_start: float, jd_end: float) -> List[float]:
    if epoch_jd is None or period_days <= 0:
        return []

    n_start = math.ceil((jd_start - epoch_jd) / period_days)
    n_end = math.floor((jd_end - epoch_jd) / period_days)
    return [epoch_jd + n * period_days for n in range(int(n_start), int(n_end) + 1)]


def _gmst_deg(jd_value: float) -> float:
    return (280.46061837 + 360.98564736629 * (jd_value - 2451545.0)) % 360.0


def _alt_az(ra_deg: float, dec_deg: float, when_utc: datetime, latitude: float, longitude: float) -> tuple[float, float]:
    jd_value = _to_jd(when_utc)
    lst_deg = (_gmst_deg(jd_value) + longitude) % 360.0
    hour_angle_deg = (lst_deg - ra_deg) % 360.0

    lat_rad = math.radians(latitude)
    dec_rad = math.radians(dec_deg)
    ha_rad = math.radians(hour_angle_deg)

    sin_alt = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt_rad = math.asin(sin_alt)

    cos_alt = max(1e-12, math.cos(alt_rad))
    sin_az = -math.cos(dec_rad) * math.sin(ha_rad) / cos_alt
    cos_az = (math.sin(dec_rad) - math.sin(alt_rad) * math.sin(lat_rad)) / (cos_alt * math.cos(lat_rad))
    az_deg = math.degrees(math.atan2(sin_az, cos_az)) % 360.0

    return math.degrees(alt_rad), az_deg


def compute_airmass_at_local_time(
    ra_deg: float,
    dec_deg: float,
    local_time: datetime,
    timezone_offset: float,
    latitude: float,
    longitude: float,
) -> Optional[float]:
    """Compute approximate airmass from local time and target coordinates."""
    when_utc = local_time - timedelta(hours=timezone_offset)
    altitude_deg, _ = _alt_az(ra_deg, dec_deg, when_utc, latitude, longitude)
    if altitude_deg <= 0:
        return None

    zenith_deg = 90.0 - altitude_deg
    cos_z = math.cos(math.radians(zenith_deg))
    if cos_z <= 0:
        return None

    airmass = 1.0 / cos_z
    if airmass <= 0 or airmass > 10:
        return None
    return airmass


def estimate_culmination_local(
    ra_deg: float,
    dec_deg: float,
    observation_date: date,
    latitude: float,
    longitude: float,
    timezone_offset: float,
    step_minutes: int = 2,
) -> datetime:
    """Estimate local culmination time (max altitude) over the observation date's 24h window."""
    start_local = datetime.combine(observation_date, datetime.min.time())
    end_local = start_local + timedelta(days=1)
    step = timedelta(minutes=max(1, step_minutes))

    best_time = start_local
    best_alt = -90.0
    current_local = start_local

    while current_local <= end_local:
        current_utc = current_local - timedelta(hours=timezone_offset)
        altitude_deg, _ = _alt_az(ra_deg, dec_deg, current_utc, latitude, longitude)
        if altitude_deg > best_alt:
            best_alt = altitude_deg
            best_time = current_local
        current_local += step

    return best_time


def minimum_altitude_during_observation_window(
    ra_deg: float,
    dec_deg: float,
    minima_utc: datetime,
    latitude: float,
    longitude: float,
    window_hours: float = 2.0,
    step_minutes: int = 30,
) -> float:
    """Return minimum altitude across [minima-window, minima+window] in degrees."""
    start_utc = minima_utc - timedelta(hours=window_hours)
    end_utc = minima_utc + timedelta(hours=window_hours)

    current = start_utc
    min_alt = float("inf")
    while current <= end_utc:
        altitude_deg, _ = _alt_az(ra_deg, dec_deg, current, latitude, longitude)
        min_alt = min(min_alt, altitude_deg)
        current += timedelta(minutes=step_minutes)

    return min_alt


def _azimuth_in_range(azimuth: float, azimuth_min: float, azimuth_max: float) -> bool:
    if azimuth_min <= azimuth_max:
        return azimuth_min <= azimuth <= azimuth_max
    return azimuth >= azimuth_min or azimuth <= azimuth_max


def _azimuth_cardinal(azimuth_deg: float) -> str:
    sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((azimuth_deg + 22.5) // 45) % 8
    return sectors[idx]


def sector_to_bounds(sector: str) -> tuple[float, float]:
    key = (sector or "").strip().upper()
    if key not in SECTOR_BOUNDS:
        raise ValueError(f"Unknown azimuth sector '{sector}'. Valid: {', '.join(SECTOR_BOUNDS.keys())}")
    return SECTOR_BOUNDS[key]


def normalize_sectors(sectors: Optional[List[str]]) -> Optional[Set[str]]:
    if not sectors:
        return None

    normalized: Set[str] = set()
    for entry in sectors:
        if not entry:
            continue
        key = entry.strip().upper()
        if key not in SECTOR_BOUNDS:
            raise ValueError(f"Unknown azimuth sector '{entry}'. Valid: {', '.join(SECTOR_BOUNDS.keys())}")
        normalized.add(key)

    return normalized or None


def _is_eclipsing_binary(variability_type: str) -> bool:
    if not variability_type:
        return False
    value = variability_type.strip().upper()
    return value.startswith("E")


def _best_target_name(row: sqlite3.Row) -> str:
    raw_name = row["desig_gcvs"] or row["desig_czev"] or row["name"] or f"CzeV{row['id']}"
    # Normalize catalog-style variable-star prefixes like "V* Y Crv" -> "Y Crv".
    return re.sub(r"^V\*\s+", "", str(raw_name).strip(), flags=re.IGNORECASE)


def get_nina_targets_export_dir(observation_date: date, telescope: str = "SCT") -> Path:
    """Return the standard NINA targets export folder: VarStars/<telescope>/YYYYMMDD."""
    telescope_name = (telescope or "SCT").upper()
    try:
        from findTargets import NINA_EXPORT_BASE_DIR

        base_dir = Path(NINA_EXPORT_BASE_DIR)
    except Exception:
        base_dir = Path(r"C:\Users\aegis\Documents\N.I.N.A\Targets\VarStars")

    if base_dir.name.lower() != "varstars":
        base_dir = base_dir / "VarStars"

    return base_dir / telescope_name / observation_date.strftime("%Y%m%d")


def find_eb_targets_for_night(
    observation_date: date,
    db_path: Path = DEFAULT_DB_PATH,
    table_name: str = DEFAULT_TABLE,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone_offset: Optional[float] = None,
    azimuth_min: float = 0.0,
    azimuth_max: float = 360.0,
    az_sector: Optional[str] = None,
    az_sectors: Optional[List[str]] = None,
    min_altitude_during_obs: float = 30.0,
) -> List[Dict]:
    defaults = _load_defaults()
    latitude = defaults["latitude"] if latitude is None else float(latitude)
    longitude = defaults["longitude"] if longitude is None else float(longitude)
    timezone_offset = defaults["timezone_offset"] if timezone_offset is None else float(timezone_offset)

    table_name = _safe_table_name(table_name)
    db_path = resolve_db_path(db_path)

    sector_filter = normalize_sectors(az_sectors)
    if az_sector:
        single_sector = az_sector.strip().upper()
        sector_filter = (sector_filter or set())
        sector_filter.add(single_sector)

    if az_sector and not sector_filter:
        azimuth_min, azimuth_max = sector_to_bounds(az_sector)

    # Restrict minima to the actual dark-sky observing window in local time.
    night_start_local, night_end_local = get_dark_night_bounds_local(observation_date, latitude, longitude)

    start_utc, end_utc = _night_window_utc(observation_date, timezone_offset)
    jd_start = _to_jd(start_utc)
    jd_end = _to_jd(end_utc)

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
        variability_type = row["variability_type"] or ""
        if not _is_eclipsing_binary(variability_type):
            continue

        period_days = float(row["period_d"])
        primary_epoch = _correct_epoch(row["epoch_hjd"])
        secondary_epoch = _correct_epoch(row["epoch_secondary_hjd"])

        minima_events: List[tuple[float, str]] = []
        minima_events.extend((jd_value, "I") for jd_value in _minima_jd_in_window(primary_epoch, period_days, jd_start, jd_end))
        minima_events.extend((jd_value, "II") for jd_value in _minima_jd_in_window(secondary_epoch, period_days, jd_start, jd_end))

        for jd_value, minima_type in minima_events:
            minima_utc = _from_jd(jd_value)
            minima_local = minima_utc + timedelta(hours=timezone_offset)

            if not (night_start_local <= minima_local < night_end_local):
                continue

            ra_deg = float(row["ra_deg"])
            dec_deg = float(row["dec_deg"])
            altitude_deg, azimuth_deg = _alt_az(ra_deg, dec_deg, minima_utc, latitude, longitude)

            az_cardinal = _azimuth_cardinal(azimuth_deg)

            if sector_filter:
                if az_cardinal not in sector_filter:
                    continue
            elif not _azimuth_in_range(azimuth_deg, azimuth_min, azimuth_max):
                continue

            min_alt_window = minimum_altitude_during_observation_window(
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                minima_utc=minima_utc,
                latitude=latitude,
                longitude=longitude,
                window_hours=2.0,
                step_minutes=30,
            )
            if min_alt_window < float(min_altitude_during_obs):
                continue

            targets.append(
                {
                    "id": str(row["id"]),
                    "name": _best_target_name(row),
                    "constellation": row["constellation"] or "",
                    "variability_type": variability_type,
                    "minima_type": minima_type,
                    "minimum_time": minima_utc.strftime("%m/%d/%y, %H:%M"),
                    "minima_datetime_utc": minima_utc,
                    "minima_datetime_local": minima_local,
                    "azimuth_deg": round(azimuth_deg, 1),
                    "azimuth": az_cardinal,
                    "altitude": f"{altitude_deg:.1f}",
                    "min_altitude_window": f"{min_alt_window:.1f}",
                    "period": str(period_days),
                    "ra": str(ra_deg),
                    "dec": str(dec_deg),
                    "ra_sexagesimal": ra_deg_to_sexagesimal(ra_deg),
                    "dec_sexagesimal": dec_deg_to_sexagesimal(dec_deg),
                    "mag_max": "" if row["mag_max"] is None else str(row["mag_max"]),
                    "mag_min": "" if row["mag_min"] is None else str(row["mag_min"]),
                }
            )

    targets.sort(key=lambda item: item["minima_datetime_utc"])
    return targets


def select_partitioned_targets(
    targets: List[Dict],
    max_targets: int,
    observation_date: date,
    latitude: float,
    longitude: float,
) -> List[Dict]:
    """
    Split the night into N partitions and select minima closest to each partition center.
    """
    if max_targets <= 0 or not targets:
        return []

    night_start, night_end = get_dark_night_bounds_local(observation_date, latitude, longitude)
    if night_end <= night_start:
        night_end = night_start + timedelta(hours=12)

    block_size = (night_end - night_start) / max_targets

    # Hard filter to dark-night local minima only.
    remaining = sorted(
        [
            item
            for item in targets
            if night_start <= item.get("minima_datetime_local") < night_end
        ],
        key=lambda item: item["minima_datetime_local"],
    )

    if not remaining:
        return []

    selected: List[Dict] = []
    used_names = set()

    for idx in range(max_targets):
        block_start = night_start + idx * block_size
        block_end = night_start + (idx + 1) * block_size
        block_center = block_start + (block_end - block_start) / 2

        in_block = [
            item for item in remaining
            if block_start <= item["minima_datetime_local"] < block_end and item.get("name") not in used_names
        ]

        candidate_pool = in_block
        if not candidate_pool:
            # If a partition has no matches, borrow the nearest event from another
            # partition, but still only from the dark-night filtered set.
            candidate_pool = [
                item
                for item in remaining
                if item.get("name") not in used_names
                and night_start <= item.get("minima_datetime_local") < night_end
            ]

        if not candidate_pool:
            break

        chosen = min(candidate_pool, key=lambda item: abs(item["minima_datetime_local"] - block_center))
        chosen = dict(chosen)
        chosen["partition_index"] = idx + 1
        chosen["partition_start_local"] = block_start
        chosen["partition_end_local"] = block_end
        chosen["partition_center_local"] = block_center

        selected.append(chosen)
        used_names.add(chosen.get("name"))
        remaining = [item for item in remaining if item is not chosen and item.get("name") != chosen.get("name")]

    selected.sort(key=lambda item: item["minima_datetime_local"])
    return selected


def export_targets_csv(targets: List[Dict], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "id",
            "name",
            "constellation",
            "variability_type",
            "minima_type",
            "minimum_time_utc",
            "minimum_time_local",
            "azimuth_deg",
            "azimuth_cardinal",
            "altitude_deg",
            "period_days",
            "ra_deg",
            "dec_deg",
            "mag_max",
            "mag_min",
        ])
        for item in targets:
            writer.writerow([
                item.get("id", ""),
                item.get("name", ""),
                item.get("constellation", ""),
                item.get("variability_type", ""),
                item.get("minima_type", ""),
                item.get("minimum_time", ""),
                item.get("minima_datetime_local", "").strftime("%Y-%m-%d %H:%M") if item.get("minima_datetime_local") else "",
                item.get("azimuth_deg", ""),
                item.get("azimuth", ""),
                item.get("altitude", ""),
                item.get("period", ""),
                item.get("ra", ""),
                item.get("dec", ""),
                item.get("mag_max", ""),
                item.get("mag_min", ""),
            ])


def export_targets_json(targets: List[Dict], output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for item in targets:
        row = dict(item)
        if row.get("minima_datetime_utc"):
            row["minima_datetime_utc"] = row["minima_datetime_utc"].isoformat()
        if row.get("minima_datetime_local"):
            row["minima_datetime_local"] = row["minima_datetime_local"].isoformat()
        if row.get("partition_start_local"):
            row["partition_start_local"] = row["partition_start_local"].isoformat()
        if row.get("partition_end_local"):
            row["partition_end_local"] = row["partition_end_local"].isoformat()
        if row.get("partition_center_local"):
            row["partition_center_local"] = row["partition_center_local"].isoformat()
        serializable.append(row)

    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2)


def export_targets_nina_sequence(
    targets: List[Dict],
    output_dir: Path,
    telescope: str = "SCT",
):
    """Export EB targets as a NINA night sequence using the existing scheduler exporter."""
    if not targets:
        return None

    from findTargets import export_to_nina_night_sequence

    export_ready_targets: List[Dict] = []
    for target in targets:
        export_target = dict(target)
        export_target_name = str(export_target.get("name", "")).strip()
        export_target["name"] = re.sub(r"^V\*\s+", "", export_target_name, flags=re.IGNORECASE)
        export_target["ra"] = export_target.get("ra_sexagesimal", export_target.get("ra", "00:00:00"))
        export_target["dec"] = export_target.get("dec_sexagesimal", export_target.get("dec", "+00:00:00"))
        export_ready_targets.append(export_target)

    return export_to_nina_night_sequence(
        export_ready_targets,
        output_dir=output_dir,
        telescope=telescope,
    )


def export_targets_nina_individual(
    targets: List[Dict],
    output_dir: Optional[Path] = None,
    telescope: str = "SCT",
    observation_date: Optional[date] = None,
):
    """Export EB targets as individual NINA target JSON files."""
    if not targets:
        return []

    if output_dir is None:
        output_dir = get_nina_targets_export_dir(observation_date or date.today(), telescope=telescope)
    output_dir.mkdir(parents=True, exist_ok=True)

    from findTargets import export_to_nina_json

    export_ready_targets: List[Dict] = []
    for target in targets:
        export_target = dict(target)
        export_target_name = str(export_target.get("name", "")).strip()
        export_target["name"] = re.sub(r"^V\*\s+", "", export_target_name, flags=re.IGNORECASE)
        export_target["ra"] = export_target.get("ra_sexagesimal", export_target.get("ra", "00:00:00"))
        export_target["dec"] = export_target.get("dec_sexagesimal", export_target.get("dec", "+00:00:00"))
        export_ready_targets.append(export_target)

    result = export_to_nina_json(
        export_ready_targets,
        output_dir=output_dir,
        mode="individual",
        telescope=telescope,
    )

    normalized_paths: List[Path] = []
    for exported in (result or []):
        exported_path = Path(exported)
        sanitized_name = re.sub(r"\s+", "_", exported_path.name)
        if sanitized_name != exported_path.name:
            sanitized_path = exported_path.with_name(sanitized_name)
            if sanitized_path.exists() and sanitized_path != exported_path:
                sanitized_path.unlink()
            exported_path.replace(sanitized_path)
            normalized_paths.append(sanitized_path)
        else:
            normalized_paths.append(exported_path)

    return normalized_paths


def main() -> None:
    defaults = _load_defaults()

    parser = argparse.ArgumentParser(description="Find eclipsing binary minima targets from varcz_eb database")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to varcz_eb.db")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Table name (default: stars)")
    parser.add_argument("--date", default=date.today().isoformat(), help="Observation date (YYYY-MM-DD)")
    parser.add_argument("--lat", type=float, default=defaults["latitude"], help="Observer latitude")
    parser.add_argument("--lon", type=float, default=defaults["longitude"], help="Observer longitude")
    parser.add_argument("--tz", type=float, default=defaults["timezone_offset"], help="Timezone offset from UTC hours")
    parser.add_argument("--az-min", type=float, default=0.0, help="Minimum azimuth degrees")
    parser.add_argument("--az-max", type=float, default=360.0, help="Maximum azimuth degrees")
    parser.add_argument("--az-sector", choices=list(SECTOR_BOUNDS.keys()), help="Broad azimuth sector override")
    parser.add_argument("--az-sectors", help="Comma-separated sectors (e.g. E,NE,NW)")
    parser.add_argument("--min-alt-obs", type=float, default=30.0, help="Minimum altitude during +/-2h observation window")
    parser.add_argument("--max-targets", type=int, default=2, help="How many events to print/export")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent / "targets", help="Output directory")
    parser.add_argument("--telescope", default="SCT", choices=["SCT", "S50"], help="NINA export telescope template")
    args = parser.parse_args()

    obs_date = date.fromisoformat(args.date)
    targets = find_eb_targets_for_night(
        observation_date=obs_date,
        db_path=args.db,
        table_name=args.table,
        latitude=args.lat,
        longitude=args.lon,
        timezone_offset=args.tz,
        azimuth_min=args.az_min,
        azimuth_max=args.az_max,
        az_sector=args.az_sector,
        az_sectors=[s.strip() for s in args.az_sectors.split(",")] if args.az_sectors else None,
        min_altitude_during_obs=args.min_alt_obs,
    )

    print(f"Found {len(targets)} matching EB minima events")

    selected = select_partitioned_targets(
        targets=targets,
        max_targets=max(0, args.max_targets),
        observation_date=obs_date,
        latitude=args.lat,
        longitude=args.lon,
    )

    night_start, night_end = get_dark_night_bounds_local(obs_date, args.lat, args.lon)
    print(f"Night bounds local: {night_start.strftime('%Y-%m-%d %H:%M')} -> {night_end.strftime('%Y-%m-%d %H:%M')}")

    for idx, item in enumerate(selected, start=1):
        print(
            f"{idx}. {item['name']} | {item['minima_type']} | UTC {item['minimum_time']} | "
            f"Local {item['minima_datetime_local'].strftime('%Y-%m-%d %H:%M')} | "
            f"Az {item['azimuth_deg']} deg ({item['azimuth']}) | "
            f"Partition {item.get('partition_index', '?')}"
        )

    if selected:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = args.out_dir / f"eb_targets_{obs_date}.csv"
        json_path = args.out_dir / f"eb_targets_{obs_date}.json"
        export_targets_csv(selected, csv_path)
        export_targets_json(selected, json_path)
        nina_sequence_path = export_targets_nina_sequence(selected, args.out_dir, telescope=args.telescope)
        print(f"Wrote {csv_path}")
        print(f"Wrote {json_path}")
        if nina_sequence_path:
            print(f"Wrote {nina_sequence_path}")


if __name__ == "__main__":
    main()
