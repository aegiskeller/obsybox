# Date Handling Fix for NINA Target Selector

## Problem Identified
The var.astro.cz website was returning targets with minima from the previous night when searching for today's date. This happened because:
1. The website defaults to yesterday's date
2. The date field wasn't being explicitly set in the web scraping code
3. URL parameters alone weren't sufficient to override the default

## Solution Implemented

### 1. **Explicit Date Field Setting**
Added code to explicitly find and set the date input field (`obsDate`) on the var.astro.cz website:

```python
# Date field - ensure it's set to the observation date (override any default)
try:
    date_input = driver.find_element(By.ID, "obsDate")
    date_input.clear()
    date_input.send_keys(obs_date.strftime('%Y-%m-%d'))
    logger.info(f"Set date field to: {obs_date.strftime('%Y-%m-%d')}")
except Exception as e:
    logger.warning(f"Could not find or set date field: {e}")
```

### 2. **Enhanced Logging**
Updated the filter application logging to include the date that was set:

```python
logger.info(f"Applied filters: date={obs_date.strftime('%Y-%m-%d')}, mag {MAG_MIN}-{MAG_MAX}, alt >{MIN_ALTITUDE}°, azimuth={azimuth_filter}")
```

### 3. **Cache Management in GUI**
Added a "🗑️ Clear Cache" button to the GUI to help with testing and troubleshooting:
- Allows users to clear cached target data
- Useful when testing date changes or when cached data becomes stale
- Shows confirmation dialog and reports number of files cleared

## Testing Strategy

### Date Logic Test Results
For observation night 2025-11-02 in Australia (UTC+10):
- **Night window (LOCAL)**: 2025-11-02 12:00 to 2025-11-03 12:00
- **Night window (UTC)**: 2025-11-02 02:00 to 2025-11-03 02:00

Target filtering results:
- ✗ Targets with minima before 02:00 UTC Nov 2 - EXCLUDED (before window)
- ✓ Targets with minima from 02:00 UTC Nov 2 to 02:00 UTC Nov 3 - INCLUDED (within window)  
- ✗ Targets with minima after 02:00 UTC Nov 3 - EXCLUDED (after window)

This confirms that the observation night window calculation correctly handles the Australian timezone (UTC+10).

## Usage Instructions

### For Users:
1. **Normal Operation**: The system now automatically sets the correct date when searching
2. **Cache Issues**: Use the "Clear Cache" button if you suspect cached data is outdated
3. **Date Verification**: Check the log output to confirm the date being sent to the website

### For Developers:
1. **Testing**: Use the "Clear Cache" button between tests to ensure fresh data
2. **Debugging**: Check the selenium log output for date field setting confirmation
3. **Cache Location**: Cache files are stored as `cache_raw_targets_YYYY-MM-DD.json`

## Technical Details

### Web Scraping Enhancement
- Added explicit date field manipulation using Selenium
- Maintains existing URL parameter approach as backup
- Graceful error handling if date field isn't found

### Cache System
- Cache files are date-specific (`cache_raw_targets_2025-11-02.json`)
- GUI provides easy cache clearing functionality
- Cache helps reduce load on var.astro.cz servers during testing

### Error Handling
- Date field setting has try/catch with warning logs
- Cache clearing operations are wrapped in error handling
- User-friendly error messages in GUI

## Expected Behavior
After this fix:
1. Searching for observation night 2025-11-02 should return targets with minima during the night of Nov 2-3
2. No more targets from the previous night appearing in current night searches
3. Cache files will be properly date-stamped and can be easily cleared when needed

This fix ensures that the target selector accurately finds targets for the intended observation night rather than defaulting to yesterday's targets.