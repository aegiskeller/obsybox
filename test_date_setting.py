"""
Test the improved date setting in findTargets.py
This will run a limited scrape to test if the date is being set correctly
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'nina_scheduling'))

from datetime import date
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Test date setting with a limited scrape
def test_date_setting():
    print("Testing date setting for observation date: 2025-11-02")
    print("This will run a limited scrape to check if the date field is being set correctly")
    
    try:
        from findTargets import fetch_minima_predictions
        
        # Run with max_pages=1 to limit the test
        obs_date = date(2025, 11, 2)
        print(f"Requesting targets for: {obs_date}")
        
        targets = fetch_minima_predictions(obs_date=obs_date, max_pages=1, use_cache=False)
        
        if targets:
            print(f"\nFound {len(targets)} targets")
            print("Checking minima dates...")
            
            date_counts = {}
            for target in targets[:10]:  # Check first 10 targets
                minima_time = target.get('minimum_time', '')
                if minima_time:
                    date_part = minima_time.split(',')[0]  # Get just the date part
                    date_counts[date_part] = date_counts.get(date_part, 0) + 1
                    print(f"  {target.get('name', 'Unknown')}: {minima_time}")
            
            print(f"\nDate distribution in first 10 targets:")
            for date_str, count in date_counts.items():
                print(f"  {date_str}: {count} targets")
                
            # Check if we're getting the right date
            if '11/02/25' in date_counts:
                print("\n✅ SUCCESS: Found targets with minima on 11/02/25!")
            elif '11/01/25' in date_counts:
                print("\n❌ FAILURE: Still getting targets from 11/01/25 (yesterday)")
            else:
                print(f"\n⚠️  UNEXPECTED: Got dates: {list(date_counts.keys())}")
        else:
            print("No targets found")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_date_setting()