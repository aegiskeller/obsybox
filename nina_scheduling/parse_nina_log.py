#!/usr/bin/env python3
"""
Parse NINA log files and import exposure information into the observation database.

This script extracts successful exposure records from NINA log files and stores them
in the observations database. It captures:
- Exposure datetime
- Image type (LIGHT, FLAT, DARK, BIAS)
- Filter used
- Exposure time
- File path

Usage:
    python parse_nina_log.py --log nina_log.log --db observations.sqlite
    python parse_nina_log.py --log nina_log.log --dry-run
"""

import re
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager


def calculate_observation_night(exposure_datetime: datetime, noon_cutoff_hour: int = 12) -> str:
    """
    Calculate the observation night for an exposure using astronomical date convention.
    
    Observations are grouped by observing night, not calendar date. An observing night
    runs from noon to noon. Exposures taken after midnight but before noon belong to
    the previous calendar date's observing night.
    
    Args:
        exposure_datetime: The datetime of the exposure
        noon_cutoff_hour: Hour marking the boundary between nights (default: 12 = noon)
        
    Returns:
        Observation night date as ISO string (YYYY-MM-DD)
        
    Examples:
        2025-10-24 20:30 → 2025-10-24  (evening of Oct 24)
        2025-10-25 00:30 → 2025-10-24  (past midnight, still Oct 24 night)
        2025-10-25 13:00 → 2025-10-25  (afternoon, now Oct 25 night)
    """
    if exposure_datetime.hour < noon_cutoff_hour:
        # Before noon - subtract one day to get previous night
        obs_night = exposure_datetime.date() - timedelta(days=1)
    else:
        # After noon - use current date
        obs_night = exposure_datetime.date()
    
    return obs_night.isoformat()


class NINALogParser:
    """Parse NINA log files and extract exposure information."""
    
    # Pattern to match successful save lines
    # Example: 2025-10-24T19:29:35.0083|INFO|BaseImageData.cs|SaveToDisk|344|Saved image to C:\Users\aegis\Documents\N.I.N.A\2025-10-24\FLAT\FlatWizard\2025-10-24_19-29-33_I_22.60_0.31s_0008.fits
    SAVE_PATTERN = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{4})\|INFO\|BaseImageData\.cs\|SaveToDisk\|\d+\|Saved image to (?P<filepath>.+)$'
    )
    
    # Pattern to extract details from filename
    # Example: 2025-10-24_19-29-33_I_22.60_0.31s_0008.fits
    # Note: temperature can be negative (e.g., -9.80)
    FILENAME_PATTERN = re.compile(
        r'(?P<datetime>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_(?P<filter>[A-Z]+)_(?P<temp>-?[\d.]+)_(?P<exposure>[\d.]+)s_(?P<number>\d+)\.(?P<ext>fits|xisf)',
        re.IGNORECASE
    )
    
    # Pattern to extract image type from path
    # Example: C:\Users\aegis\Documents\N.I.N.A\2025-10-24\FLAT\FlatWizard\...
    IMAGE_TYPE_PATTERN = re.compile(
        r'[\\/](?P<image_type>LIGHT|FLAT|DARK|BIAS)[\\/]',
        re.IGNORECASE
    )
    
    # Pattern to extract profile ID from config line
    # Example: 2025-10-24T14:40:47.1393|INFO|DockManagerVM.cs|InitializeAvalonDockLayout|356|Initializing imaging tab layout from C:\Users\aegis\AppData\Local\NINA\Profiles\ddf033e5-b0e2-4daf-9ebe-71b46a091495.dock.config
    PROFILE_PATTERN = re.compile(
        r'InitializeAvalonDockLayout.*Profiles[\\/](?P<profile_id>[a-f0-9\-]{36})\.dock\.config',
        re.IGNORECASE
    )
    
    def __init__(self, db_path: Optional[str] = None, profile_map: Optional[Dict[str, str]] = None):
        """Initialize parser with optional database path and profile mapping.
        
        Args:
            db_path: Path to SQLite database
            profile_map: Dictionary mapping profile IDs to telescope names
        """
        self.db_path = Path(db_path) if db_path else None
        self.profile_map = profile_map or {}
        self.exposures: List[Dict] = []
        self.detected_profile: Optional[str] = None
        self.telescope_name: Optional[str] = None
        
    @contextmanager
    def get_connection(self):
        """Get a database connection with context management."""
        if not self.db_path:
            raise ValueError("No database path specified")
        
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def parse_log_file(self, log_path: Path) -> List[Dict]:
        """
        Parse a NINA log file and extract exposure information.
        
        Args:
            log_path: Path to the NINA log file
            
        Returns:
            List of exposure dictionaries with extracted information
        """
        self.exposures = []
        self.log_path = log_path  # Store for database tracking
        
        # Read entire file and normalize line endings
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Replace all types of line endings with spaces (paths can span multiple lines)
        # But first protect actual line breaks between log entries
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Process line by line, but join continuation lines
        lines = content.split('\n')
        processed_lines = []
        current_line = ""
        
        for line in lines:
            # Check if this looks like the start of a new log entry (timestamp pattern)
            if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{4}\|', line):
                # Save previous line if it exists
                if current_line:
                    processed_lines.append(current_line)
                current_line = line
            else:
                # This is a continuation of the previous line - join without space
                # since paths shouldn't have spaces added in the middle
                current_line += line.strip()
        
        # Don't forget the last line
        if current_line:
            processed_lines.append(current_line)
        
        # First pass: detect profile ID
        self._detect_profile(processed_lines)
        
        # Second pass: process the joined lines to extract exposures
        for line_num, line in enumerate(processed_lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a successful save line
            match = self.SAVE_PATTERN.match(line)
            if not match:
                continue
            
            # Extract basic info
            log_timestamp = match.group('timestamp')
            file_path = match.group('filepath')
            
            # Parse the file path for details
            exposure_info = self._parse_file_path(file_path, log_timestamp, line_num)
            if exposure_info:
                self.exposures.append(exposure_info)
        
        return self.exposures
    
    def _detect_profile(self, lines: List[str]) -> None:
        """
        Detect the NINA profile ID from the log file.
        
        Looks for the InitializeAvalonDockLayout line which contains the profile ID.
        Example: ...Profiles\ddf033e5-b0e2-4daf-9ebe-71b46a091495.dock.config
        
        Args:
            lines: List of processed log lines
        """
        for line in lines:
            match = self.PROFILE_PATTERN.search(line)
            if match:
                self.detected_profile = match.group('profile_id')
                # Look up telescope name from profile map
                self.telescope_name = self.profile_map.get(self.detected_profile, self.detected_profile)
                break
    
    def _parse_file_path(self, file_path: str, log_timestamp: str, line_num: int) -> Optional[Dict]:
        """
        Parse file path to extract exposure details.
        
        Args:
            file_path: Full path to the saved image file
            log_timestamp: Timestamp from the log line
            line_num: Line number in log file (for error reporting)
            
        Returns:
            Dictionary with exposure information or None if parsing fails
        """
        # Skip PlateSolver temp files
        if 'PlateSolver' in file_path or 'PlateSolve' in file_path:
            return None
        
        # Extract image type from path
        image_type_match = self.IMAGE_TYPE_PATTERN.search(file_path)
        image_type = image_type_match.group('image_type').upper() if image_type_match else 'UNKNOWN'
        
        # Extract target name from path for LIGHT frames
        # Example: C:\Users\aegis\Documents\N.I.N.A\2025-10-24\LIGHT\EG Scl\2025-10-24_20-39-30_V_-9.80_50.00s_0000.fits
        target_name = None
        if image_type == 'LIGHT':
            # Try to extract target name (directory name after LIGHT)
            light_match = re.search(r'[\\/]LIGHT[\\/]([^\\/]+)[\\/]', file_path, re.IGNORECASE)
            if light_match:
                target_name = light_match.group(1)
        
        # Extract filename - handle both Unix and Windows path separators
        # since the log file contains Windows paths but we're running on Unix
        filename = file_path.replace('/', '\\').split('\\')[-1]
        
        # Parse filename for details
        filename_match = self.FILENAME_PATTERN.match(filename)
        if not filename_match:
            # Print repr to see actual string with escape sequences
            print(f"Warning: Could not parse filename at line {line_num}: {repr(filename)}")
            return None
        
        # Extract components
        datetime_str = filename_match.group('datetime')
        filter_name = filename_match.group('filter')
        temperature = float(filename_match.group('temp'))
        exposure_time = float(filename_match.group('exposure'))
        
        # Parse datetime (format: 2025-10-24_19-29-33)
        try:
            exposure_datetime = datetime.strptime(datetime_str, '%Y-%m-%d_%H-%M-%S')
        except ValueError as e:
            print(f"Warning: Could not parse datetime at line {line_num}: {datetime_str} - {e}")
            return None
        
        # Parse log timestamp
        try:
            log_datetime = datetime.strptime(log_timestamp, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError as e:
            print(f"Warning: Could not parse log timestamp at line {line_num}: {log_timestamp} - {e}")
            log_datetime = None
        
        return {
            'file_path': file_path,
            'filename': filename,
            'exposure_datetime': exposure_datetime,
            'log_datetime': log_datetime,
            'image_type': image_type,
            'target_name': target_name,
            'filter': filter_name,
            'exposure_time': exposure_time,
            'temperature': temperature,
            'line_number': line_num
        }
    
    def _ensure_log_table(self, conn):
        """Create the nina_log_exposures table if it doesn't exist."""
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nina_log_exposures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                exposure_datetime DATETIME NOT NULL,
                observation_night DATE,
                log_timestamp DATETIME,
                image_type TEXT NOT NULL,
                target_name TEXT,
                filter TEXT NOT NULL,
                exposure_time REAL NOT NULL,
                temperature REAL,
                telescope TEXT,
                log_file TEXT,
                scheduled BOOLEAN DEFAULT 0,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create table to track scheduled targets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nina_scheduled_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_name TEXT NOT NULL,
                ra TEXT,
                dec TEXT,
                constellation TEXT,
                magnitude_max REAL,
                magnitude_min REAL,
                minima_type TEXT,
                variability_type TEXT,
                scheduled_for_night DATE NOT NULL,
                observed_on DATE,
                telescope TEXT,
                scheduled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(target_name, scheduled_for_night, telescope)
            )
        ''')
        
        # Create table to track imported log files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nina_log_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_filename TEXT NOT NULL UNIQUE,
                log_filepath TEXT NOT NULL,
                telescope TEXT,
                profile_id TEXT,
                observation_date DATE,
                first_exposure DATETIME,
                last_exposure DATETIME,
                exposure_count INTEGER,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on exposure_datetime for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_log_exposures_datetime 
            ON nina_log_exposures(exposure_datetime)
        ''')
        
        # Create index on image_type for filtering
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_log_exposures_type 
            ON nina_log_exposures(image_type)
        ''')
        
        # Create index on log_file for tracking
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_log_exposures_logfile 
            ON nina_log_exposures(log_file)
        ''')
    
    def write_to_database(self, telescope: Optional[str] = None, dry_run: bool = False) -> Dict[str, int]:
        """
        Write parsed exposures to the database.
        
        Args:
            telescope: Name of the telescope (optional, will use detected name if not provided)
            dry_run: If True, only print what would be inserted
            
        Returns:
            Dictionary with statistics (inserted, skipped, errors)
        """
        if not self.exposures:
            print("No exposures to write")
            return {'inserted': 0, 'skipped': 0, 'errors': 0}
        
        # Use provided telescope name, or detected name, or 'Unknown'
        telescope_name = telescope or self.telescope_name or 'Unknown'
        
        stats = {'inserted': 0, 'skipped': 0, 'errors': 0}
        
        if dry_run:
            print(f"\nDry run: Would insert {len(self.exposures)} exposures")
            for exp in self.exposures[:5]:  # Show first 5
                target = f" | {exp['target_name']}" if exp.get('target_name') else ""
                print(f"  {exp['exposure_datetime']} | {exp['image_type']:5s}{target} | {exp['filter']:2s} | {exp['exposure_time']:6.2f}s | {exp['filename']}")
            if len(self.exposures) > 5:
                print(f"  ... and {len(self.exposures) - 5} more")
            stats['inserted'] = len(self.exposures)
            return stats
        
        with self.get_connection() as conn:
            # Ensure table exists
            self._ensure_log_table(conn)
            
            cursor = conn.cursor()
            
            # Check if this log file was already imported
            cursor.execute('''
                SELECT exposure_count, imported_at 
                FROM nina_log_files 
                WHERE log_filename = ?
            ''', (self.log_path.name,))
            
            existing = cursor.fetchone()
            if existing:
                print(f"\nNote: This log file was previously imported on {existing[1]}")
                print(f"      ({existing[0]} exposures). Duplicate exposures will be skipped.\n")
            
            for exp in self.exposures:
                try:
                    # Calculate observation night (astronomical date)
                    obs_night = calculate_observation_night(exp['exposure_datetime'])
                    
                    # Insert into nina_log_exposures table
                    cursor.execute('''
                        INSERT INTO nina_log_exposures (
                            file_path,
                            filename,
                            exposure_datetime,
                            observation_night,
                            log_timestamp,
                            image_type,
                            target_name,
                            filter,
                            exposure_time,
                            temperature,
                            telescope,
                            log_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        exp['file_path'],
                        exp['filename'],
                        exp['exposure_datetime'].isoformat(),
                        obs_night,
                        exp['log_datetime'].isoformat() if exp['log_datetime'] else None,
                        exp['image_type'],
                        exp.get('target_name'),
                        exp['filter'],
                        exp['exposure_time'],
                        exp['temperature'],
                        telescope_name,
                        self.log_path.name if hasattr(self, 'log_path') else None
                    ))
                    stats['inserted'] += 1
                    
                except sqlite3.IntegrityError:
                    # Probably a duplicate
                    stats['skipped'] += 1
                    
                except Exception as e:
                    print(f"Error inserting exposure at line {exp['line_number']}: {e}")
                    stats['errors'] += 1
            
            # Register the log file in tracking table
            if stats['inserted'] > 0 and hasattr(self, 'log_path'):
                self._register_log_file(cursor, telescope_name, stats['inserted'])
        
        return stats
    
    def _register_log_file(self, cursor, telescope_name: str, exposure_count: int) -> None:
        """Register the imported log file in the tracking table."""
        if not self.exposures:
            return
        
        # Calculate date range from exposures
        exposure_times = [exp['exposure_datetime'] for exp in self.exposures]
        first_exposure = min(exposure_times)
        last_exposure = max(exposure_times)
        observation_date = first_exposure.date()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO nina_log_files (
                    log_filename,
                    log_filepath,
                    telescope,
                    profile_id,
                    observation_date,
                    first_exposure,
                    last_exposure,
                    exposure_count,
                    imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                self.log_path.name,
                str(self.log_path.absolute()),
                telescope_name,
                self.detected_profile,
                observation_date.isoformat(),
                first_exposure.isoformat(),
                last_exposure.isoformat(),
                exposure_count
            ))
        except Exception as e:
            print(f"Warning: Could not register log file: {e}")
    
    def print_summary(self):
        """Print a summary of parsed exposures."""
        if not self.exposures:
            print("No exposures found")
            return
        
        print(f"\nParsed {len(self.exposures)} exposures")
        
        # Group by image type
        by_type = {}
        for exp in self.exposures:
            img_type = exp['image_type']
            by_type[img_type] = by_type.get(img_type, 0) + 1
        
        print("\nBy image type:")
        for img_type, count in sorted(by_type.items()):
            print(f"  {img_type:6s}: {count:4d}")
        
        # Group by filter
        by_filter = {}
        for exp in self.exposures:
            filter_name = exp['filter']
            by_filter[filter_name] = by_filter.get(filter_name, 0) + 1
        
        print("\nBy filter:")
        for filter_name, count in sorted(by_filter.items()):
            print(f"  {filter_name:2s}: {count:4d}")
        
        # Date range
        dates = [exp['exposure_datetime'] for exp in self.exposures]
        print(f"\nDate range: {min(dates).date()} to {max(dates).date()}")
        
        # Exposure time stats
        exp_times = [exp['exposure_time'] for exp in self.exposures]
        print(f"Exposure times: {min(exp_times):.2f}s to {max(exp_times):.2f}s")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Parse NINA log files and import exposure information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Parse log and show summary (auto-detects telescope from profile)
  python parse_nina_log.py --log nina.log
  
  # Parse and import to database (auto-detects telescope)
  python parse_nina_log.py --log nina.log --db observations.sqlite
  
  # Override telescope name
  python parse_nina_log.py --log nina.log --db observations.sqlite --telescope "SCT 11-inch"
  
  # Dry run to see what would be imported
  python parse_nina_log.py --log nina.log --db observations.sqlite --dry-run
  
  # Map profile IDs to telescope names
  python parse_nina_log.py --log nina.log --db observations.sqlite --profile-map profiles.txt
        '''
    )
    
    parser.add_argument('--log', required=True, type=Path,
                       help='Path to NINA log file')
    parser.add_argument('--db', type=Path,
                       help='Path to SQLite database (optional, for import)')
    parser.add_argument('--telescope', type=str,
                       help='Telescope name (optional, overrides auto-detection)')
    parser.add_argument('--profile-map', type=Path,
                       help='File mapping profile IDs to telescope names (format: profile_id=telescope_name)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Parse but do not write to database')
    
    return parser.parse_args()


def load_profile_map(map_file: Path) -> Dict[str, str]:
    """
    Load profile ID to telescope name mapping from file.
    
    Format: one mapping per line as "profile_id=telescope_name"
    Example: ddf033e5-b0e2-4daf-9ebe-71b46a091495=SCT 8-inch
    
    Args:
        map_file: Path to mapping file
        
    Returns:
        Dictionary mapping profile IDs to telescope names
    """
    profile_map = {}
    if map_file and map_file.exists():
        with open(map_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        profile_id, telescope = line.split('=', 1)
                        profile_map[profile_id.strip()] = telescope.strip()
    return profile_map


def mark_targets_scheduled(db_path: Path, targets, observation_date: str, telescope: str = None) -> int:
    """
    Mark targets as scheduled in the database.
    
    This function:
    1. Creates/updates records in nina_scheduled_targets for each target
    2. Marks any existing exposures for those targets as scheduled
    3. Updates observed_on if exposures are found
    
    Args:
        db_path: Path to database
        targets: List of target dictionaries (with 'name', 'ra', 'dec', etc.) or list of target name strings
        observation_date: Date scheduled for in YYYY-MM-DD format (scheduled_for_night)
        telescope: Telescope name (optional)
        
    Returns:
        Number of exposures marked as scheduled
    """
    if not db_path.exists():
        # Create database if it doesn't exist
        print(f"Creating database: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Ensure tables exist
    parser = NINALogParser(db_path=db_path)
    with parser.get_connection() as conn2:
        parser._ensure_log_table(conn2)
    
    marked = 0
    for target in targets:
        try:
            # Handle both dictionary and string inputs
            if isinstance(target, dict):
                target_name = target.get('name', target.get('Star', 'Unknown'))
                ra = target.get('ra', target.get('RA'))
                dec = target.get('dec', target.get('Dec'))
                constellation = target.get('constellation')
                mag_max = target.get('magnitude_max', target.get('mag_max'))
                mag_min = target.get('magnitude_min', target.get('mag_min'))
                minima_type = target.get('minima_type')
                var_type = target.get('variability_type', target.get('var_type'))
            else:
                # String input - just the target name
                target_name = target
                ra = dec = constellation = mag_max = mag_min = minima_type = var_type = None
            
            # Always register in scheduled_targets table
            # Each scheduling creates a new entry (no UNIQUE constraint)
            # This allows tracking multiple scheduling attempts for the same target
            cursor.execute('''
                INSERT INTO nina_scheduled_targets 
                (target_name, ra, dec, constellation, magnitude_max, magnitude_min, 
                 minima_type, variability_type, scheduled_for_night, telescope)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (target_name, ra, dec, constellation, mag_max, mag_min, 
                  minima_type, var_type, observation_date, telescope))
            
            # Check if any exposures exist for this target on this date
            cursor.execute('''
                SELECT COUNT(*) FROM nina_log_exposures
                WHERE target_name = ?
                AND observation_night = ?
                AND (? IS NULL OR telescope = ?)
            ''', (target_name, observation_date, telescope, telescope))
            
            exposure_count = cursor.fetchone()[0]
            
            if exposure_count > 0:
                # Mark exposures as scheduled
                cursor.execute('''
                    UPDATE nina_log_exposures
                    SET scheduled = 1
                    WHERE target_name = ?
                    AND observation_night = ?
                    AND (? IS NULL OR telescope = ?)
                ''', (target_name, observation_date, telescope, telescope))
                
                marked += cursor.rowcount
                
                # Update observed_on in the most recently scheduled entry
                # (in case target was scheduled multiple times for the same night)
                cursor.execute('''
                    UPDATE nina_scheduled_targets
                    SET observed_on = ?
                    WHERE id = (
                        SELECT id FROM nina_scheduled_targets
                        WHERE target_name = ?
                        AND scheduled_for_night = ?
                        AND (? IS NULL OR telescope = ?)
                        AND observed_on IS NULL
                        ORDER BY scheduled_at DESC
                        LIMIT 1
                    )
                ''', (observation_date, target_name, observation_date, telescope, telescope))
                
        except Exception as e:
            target_display = target_name if 'target_name' in locals() else str(target)
            print(f"Warning: Could not mark target {target_display}: {e}")
    
    conn.commit()
    conn.close()
    
    return marked


def main():
    """Main entry point."""
    args = parse_args()
    
    # Validate log file
    if not args.log.exists():
        print(f"Error: Log file not found: {args.log}")
        return 1
    
    # Load profile map if provided
    profile_map = load_profile_map(args.profile_map) if args.profile_map else {}
    
    # Create parser
    parser_obj = NINALogParser(db_path=args.db, profile_map=profile_map)
    
    # Parse log file
    print(f"Parsing log file: {args.log}")
    exposures = parser_obj.parse_log_file(args.log)
    
    # Report detected profile
    if parser_obj.detected_profile:
        print(f"Detected profile: {parser_obj.detected_profile}")
        print(f"Telescope: {parser_obj.telescope_name}")
    
    # Print summary
    parser_obj.print_summary()
    
    # Write to database if requested
    if args.db or args.dry_run:
        stats = parser_obj.write_to_database(
            telescope=args.telescope,
            dry_run=args.dry_run
        )
        
        print(f"\nDatabase import:")
        print(f"  Inserted: {stats['inserted']}")
        print(f"  Skipped:  {stats['skipped']}")
        print(f"  Errors:   {stats['errors']}")
    
    return 0


if __name__ == '__main__':
    exit(main())
