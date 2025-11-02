"""
Quick validation script to check if the date format fix worked
Run this after generating targets through the GUI
"""

import json
import glob
from pathlib import Path
from datetime import date

def main():
    print("🔍 Checking for cache files after target generation...")
    
    # Look for cache files
    cache_files = glob.glob("cache_raw_targets_*.json")
    
    if not cache_files:
        print("❌ No cache files found!")
        print("   Make sure to run the GUI and click 'Generate Targets' first")
        return
    
    # Get the most recent cache file
    latest_cache = max(cache_files, key=lambda x: Path(x).stat().st_mtime)
    print(f"📄 Found cache file: {latest_cache}")
    
    # Load and analyze
    try:
        with open(latest_cache, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            print("⚠️  Cache file is empty")
            return
        
        print(f"📊 Loaded {len(data)} targets")
        
        # Check dates in the first few targets
        date_analysis = {}
        sample_count = min(10, len(data))
        
        print(f"\n🎯 Analyzing first {sample_count} targets:")
        for i, target in enumerate(data[:sample_count]):
            name = target.get('name', 'Unknown')
            minima_time = target.get('minimum_time', '')
            
            print(f"   {i+1:2d}. {name}: {minima_time}")
            
            if minima_time:
                # Extract date (format should be MM/DD/YY, ...)
                date_part = minima_time.split(',')[0].strip()
                date_analysis[date_part] = date_analysis.get(date_part, 0) + 1
        
        print(f"\n📅 Date distribution in sample:")
        for date_str, count in sorted(date_analysis.items()):
            print(f"   {date_str}: {count} targets")
        
        # Check for today vs yesterday
        today_expected = "11/02/25"  # November 2, 2025
        yesterday = "11/01/25"       # November 1, 2025
        
        if today_expected in date_analysis:
            print(f"\n✅ SUCCESS! Found targets for today ({today_expected})")
            print("   The DD/MM/YYYY date format fix is working!")
        elif yesterday in date_analysis:
            print(f"\n❌ PROBLEM: Still getting targets for yesterday ({yesterday})")
            print("   The date format fix may need more work")
        else:
            print(f"\n⚠️  UNEXPECTED: Found targets for other dates")
            print("   Check the date format or filtering logic")
        
    except Exception as e:
        print(f"❌ Error reading cache file: {e}")

if __name__ == "__main__":
    main()