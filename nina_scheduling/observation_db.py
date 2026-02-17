#!/usr/bin/env python3
"""
Observation Database Manager

Manages the astronomical observation database including sequences, nights,
targets, scheduled targets, and individual observations.

This module provides a high-level interface to the observation database schema.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import date, datetime, time
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ObservationDB:
    """Database manager for astronomical observations"""
    
    def __init__(self, db_path: str = "Z:/scheduled_observations.sqlite"):
        """Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_database(self):
        """Initialize database with schema"""
        schema_file = Path(__file__).parent / "schema.sql"
        if not schema_file.exists():
            logger.warning("Schema file not found: %s", schema_file)
            return
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        with self.get_connection() as conn:
            conn.executescript(schema_sql)
        
        logger.info("Database initialized: %s", self.db_path)
    
    # ========================================================================
    # SEQUENCES
    # ========================================================================
    
    def add_sequence(self, sequence_name: str, file_path: Optional[str] = None,
                    template_used: Optional[str] = None, notes: Optional[str] = None) -> int:
        """Add a new sequence file
        
        Args:
            sequence_name: Name of the sequence (e.g., "G6432.00592")
            file_path: Full path to the .json file
            template_used: Template file it was based on
            notes: Additional notes
            
        Returns:
            sequence_id of the inserted/existing sequence
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO sequences (sequence_name, sequence_file_path, template_used, notes)
                VALUES (?, ?, ?, ?)
            """, (sequence_name, file_path, template_used, notes))
            
            if cur.rowcount == 0:
                # Already exists, get the ID
                cur.execute("SELECT sequence_id FROM sequences WHERE sequence_name = ?", (sequence_name,))
                return cur.fetchone()[0]
            
            return cur.lastrowid
    
    def get_sequence(self, sequence_name: str) -> Optional[Dict[str, Any]]:
        """Get sequence by name"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sequences WHERE sequence_name = ?", (sequence_name,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    # ========================================================================
    # OBSERVATION NIGHTS
    # ========================================================================
    
    def add_night(self, date_obs: str, telescope: Optional[str] = None,
                  observer: Optional[str] = None, **kwargs) -> int:
        """Add a new observation night
        
        Args:
            date_obs: Observation date (YYYY-MM-DD)
            telescope: Telescope identifier
            observer: Observer name
            **kwargs: Additional fields (weather_conditions, seeing_arcsec, etc.)
            
        Returns:
            night_id of the inserted/existing night
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Build dynamic insert
            fields = ['date_obs', 'telescope', 'observer']
            values = [date_obs, telescope, observer]
            
            for key, value in kwargs.items():
                if key in ['weather_conditions', 'seeing_arcsec', 'dark_sky_start', 'dark_sky_end', 'notes']:
                    fields.append(key)
                    values.append(value)
            
            placeholders = ','.join(['?'] * len(fields))
            field_names = ','.join(fields)
            
            cur.execute(f"""
                INSERT OR IGNORE INTO observation_nights ({field_names})
                VALUES ({placeholders})
            """, values)
            
            if cur.rowcount == 0:
                # Already exists, get the ID
                cur.execute("SELECT night_id FROM observation_nights WHERE date_obs = ?", (date_obs,))
                return cur.fetchone()[0]
            
            return cur.lastrowid
    
    def get_night(self, date_obs: str) -> Optional[Dict[str, Any]]:
        """Get night by date"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM observation_nights WHERE date_obs = ?", (date_obs,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    # ========================================================================
    # TARGETS
    # ========================================================================
    
    def add_target(self, target_name: str, target_type: Optional[str] = None,
                   ra_hours: Optional[int] = None, ra_minutes: Optional[int] = None,
                   ra_seconds: Optional[float] = None, dec_degrees: Optional[int] = None,
                   dec_minutes: Optional[int] = None, dec_seconds: Optional[float] = None,
                   dec_negative: Optional[bool] = None, **kwargs) -> int:
        """Add a new target
        
        Args:
            target_name: Target name (e.g., "G6432.00592")
            target_type: Type (e.g., "variable_star")
            ra_hours, ra_minutes, ra_seconds: RA components
            dec_degrees, dec_minutes, dec_seconds, dec_negative: Dec components
            **kwargs: Additional fields (constellation, magnitude_max, etc.)
            
        Returns:
            target_id of the inserted/existing target
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            # Build field list
            fields = {
                'target_name': target_name,
                'target_type': target_type,
                'ra_hours': ra_hours,
                'ra_minutes': ra_minutes,
                'ra_seconds': ra_seconds,
                'dec_degrees': dec_degrees,
                'dec_minutes': dec_minutes,
                'dec_seconds': dec_seconds,
                'dec_negative': dec_negative,
            }
            
            # Add optional fields
            optional_fields = ['constellation', 'magnitude_max', 'magnitude_min', 
                             'variability_type', 'period_days', 'catalog_id', 
                             'gcvs_name', 'wds_identifier', 'notes']
            for field in optional_fields:
                if field in kwargs:
                    fields[field] = kwargs[field]
            
            # Remove None values
            fields = {k: v for k, v in fields.items() if v is not None}
            
            field_names = ','.join(fields.keys())
            placeholders = ','.join(['?'] * len(fields))
            
            cur.execute(f"""
                INSERT OR IGNORE INTO targets ({field_names})
                VALUES ({placeholders})
            """, list(fields.values()))
            
            if cur.rowcount == 0:
                # Already exists, get the ID
                cur.execute("SELECT target_id FROM targets WHERE target_name = ?", (target_name,))
                return cur.fetchone()[0]
            
            return cur.lastrowid
    
    def get_target(self, target_name: str) -> Optional[Dict[str, Any]]:
        """Get target by name"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM targets WHERE target_name = ?", (target_name,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    # ========================================================================
    # SCHEDULED TARGETS
    # ========================================================================
    
    def schedule_target(self, night_id: int, target_id: int,
                       scheduled_start_time: Optional[str] = None,
                       scheduled_end_time: Optional[str] = None,
                       minima_time: Optional[str] = None,
                       sequence_id: Optional[int] = None,
                       observation_window_hours: Optional[float] = None,
                       **kwargs) -> int:
        """Schedule a target for a specific night
        
        Args:
            night_id: Night ID
            target_id: Target ID
            scheduled_start_time: Start time (ISO format datetime)
            scheduled_end_time: End time (ISO format datetime)
            minima_time: Expected minima time (ISO format datetime)
            sequence_id: Sequence file used
            observation_window_hours: Planned observation duration
            **kwargs: Additional fields
            
        Returns:
            scheduled_target_id
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            fields = {
                'night_id': night_id,
                'target_id': target_id,
                'sequence_id': sequence_id,
                'scheduled_start_time': scheduled_start_time,
                'scheduled_end_time': scheduled_end_time,
                'minima_time': minima_time,
                'observation_window_hours': observation_window_hours,
            }
            
            # Add optional fields
            optional_fields = ['status', 'completion_percentage', 'notes']
            for field in optional_fields:
                if field in kwargs:
                    fields[field] = kwargs[field]
            
            # Remove None values
            fields = {k: v for k, v in fields.items() if v is not None}
            
            field_names = ','.join(fields.keys())
            placeholders = ','.join(['?'] * len(fields))
            
            cur.execute(f"""
                INSERT INTO scheduled_targets ({field_names})
                VALUES ({placeholders})
            """, list(fields.values()))
            
            return cur.lastrowid
    
    def get_scheduled_targets(self, night_id: int) -> List[Dict[str, Any]]:
        """Get all scheduled targets for a night"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT st.*, t.target_name, s.sequence_name
                FROM scheduled_targets st
                JOIN targets t ON st.target_id = t.target_id
                LEFT JOIN sequences s ON st.sequence_id = s.sequence_id
                WHERE st.night_id = ?
                ORDER BY st.scheduled_start_time
            """, (night_id,))
            return [dict(row) for row in cur.fetchall()]
    
    # ========================================================================
    # OBSERVATIONS
    # ========================================================================
    
    def add_observation(self, scheduled_target_id: int, file_path: str,
                       file_name: str, exposure_time_sec: float,
                       **kwargs) -> int:
        """Add a new observation (image capture)
        
        Args:
            scheduled_target_id: Scheduled target ID
            file_path: Full path to image file
            file_name: Filename
            exposure_time_sec: Exposure time in seconds
            **kwargs: Additional fields (filter_name, binning, datetime_start, etc.)
            
        Returns:
            observation_id
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            fields = {
                'scheduled_target_id': scheduled_target_id,
                'file_path': file_path,
                'file_name': file_name,
                'exposure_time_sec': exposure_time_sec,
            }
            
            # Add all optional fields
            optional_fields = [
                'file_size_bytes', 'file_format', 'filter_name', 'binning', 'gain', 'offset',
                'datetime_start', 'datetime_end', 'julian_date', 'guiding_enabled',
                'guiding_rms_arcsec', 'guiding_rms_ra_arcsec', 'guiding_rms_dec_arcsec',
                'fwhm_arcsec', 'hfr', 'eccentricity', 'stars_detected', 'background_adu',
                'temperature_c', 'humidity_percent', 'pressure_mbar',
                'telescope_ra', 'telescope_dec', 'telescope_alt', 'telescope_az', 'airmass',
                'calibrated', 'plate_solved', 'processed', 'included_in_analysis',
                'quality_flag', 'rejection_reason', 'notes'
            ]
            
            for field in optional_fields:
                if field in kwargs:
                    fields[field] = kwargs[field]
            
            field_names = ','.join(fields.keys())
            placeholders = ','.join(['?'] * len(fields))
            
            cur.execute(f"""
                INSERT INTO observations ({field_names})
                VALUES ({placeholders})
            """, list(fields.values()))
            
            return cur.lastrowid
    
    def get_observations(self, scheduled_target_id: int) -> List[Dict[str, Any]]:
        """Get all observations for a scheduled target"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM observations
                WHERE scheduled_target_id = ?
                ORDER BY datetime_start
            """, (scheduled_target_id,))
            return [dict(row) for row in cur.fetchall()]
    
    # ========================================================================
    # SCANNING LIGHT DIRECTORIES
    # ========================================================================
    
    def import_light_subdirs(self, base_path: Path, telescope: str = "SCT",
                            dry_run: bool = False) -> Dict[str, int]:
        """Import LIGHT subdirectories into database
        
        Args:
            base_path: Base path to scan for LIGHT directories
            telescope: Telescope identifier
            dry_run: If True, don't insert, just report
            
        Returns:
            Dictionary with statistics: {targets_added, nights_added, scheduled_added}
        """
        from find_light_subdirs import find_light_subdirs
        
        stats = {'targets_added': 0, 'nights_added': 0, 'scheduled_added': 0}
        
        # Find all LIGHT subdirectories
        results = find_light_subdirs(base_path)
        
        if not results:
            logger.info("No LIGHT subdirectories found")
            return stats
        
        logger.info("Found %d subdirectories in LIGHT folders", len(results))
        
        if dry_run:
            for r in results:
                logger.info("Would process: %s (date: %s)", r['subdir'], r.get('dateobs', 'N/A'))
            return stats
        
        # Process each result
        for r in results:
            target_name = r['subdir']
            date_obs = r.get('dateobs') or date.today().isoformat()
            
            # Add target if it doesn't exist
            target_id = self.add_target(target_name, target_type='variable_star')
            if target_id:
                stats['targets_added'] += 1
            
            # Add night if it doesn't exist
            night_id = self.add_night(date_obs, telescope=telescope)
            if night_id:
                stats['nights_added'] += 1
            
            # Check if this target is already scheduled for this night
            existing = self.get_scheduled_targets(night_id)
            target_ids = [st['target_id'] for st in existing]
            
            if target_id not in target_ids:
                # Schedule the target
                scheduled_id = self.schedule_target(
                    night_id=night_id,
                    target_id=target_id,
                    status='completed',  # Assume completed if data exists
                    notes=f"Imported from {r['light']}"
                )
                stats['scheduled_added'] += 1
        
        logger.info("Import complete: %s", stats)
        return stats
    
    # ========================================================================
    # QUERIES AND REPORTS
    # ========================================================================
    
    def get_nightly_summary(self, date_obs: str) -> Dict[str, Any]:
        """Get summary statistics for a night"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM v_nightly_statistics
                WHERE date_obs = ?
            """, (date_obs,))
            row = cur.fetchone()
            return dict(row) if row else {}
    
    def get_target_history(self, target_name: str) -> Dict[str, Any]:
        """Get observation history for a target"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM v_target_history
                WHERE target_name = ?
            """, (target_name,))
            row = cur.fetchone()
            return dict(row) if row else {}
    
    def get_recent_nights(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent observation nights"""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM v_nightly_statistics
                ORDER BY date_obs DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Observation Database Manager')
    parser.add_argument('--db', default='Z:/scheduled_observations.sqlite', help='Database path')
    parser.add_argument('--init', action='store_true', help='Initialize database')
    parser.add_argument('--scan', type=str, help='Scan base path for LIGHT directories')
    parser.add_argument('--telescope', default='SCT', help='Telescope name')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--summary', type=str, help='Get summary for date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    db = ObservationDB(args.db)
    
    if args.init:
        logger.info("Database initialized")
    
    if args.scan:
        stats = db.import_light_subdirs(
            Path(args.scan),
            telescope=args.telescope,
            dry_run=args.dry_run
        )
        logger.info("Import statistics: %s", stats)
    
    if args.summary:
        summary = db.get_nightly_summary(args.summary)
        if summary:
            print(f"\nNightly Summary for {args.summary}:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
        else:
            print(f"No data found for {args.summary}")


if __name__ == '__main__':
    main()
