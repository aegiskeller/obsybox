"""
Comprehensive test of the DD/MM/YYYY date format fix
Tests the date formatting logic and verifies cache files
"""

import sys
import os
from datetime import date
from pathlib import Path
import json

def test_date_format_logic():
    """Test that our date format conversion is correct"""
    print("🧪 Testing Date Format Logic")
    print("-" * 40)
    
    # Test date: November 2, 2025
    test_date = date(2025, 11, 2)
    
    # Old format (what was causing the problem)
    old_format = test_date.strftime('%Y-%m-%d')
    
    # New format (DD/MM/YYYY - what var.astro.cz expects)
    new_format = test_date.strftime('%d/%m/%Y')
    
    print(f"Test date: {test_date}")
    print(f"Old format (YYYY-MM-DD): {old_format}")
    print(f"New format (DD/MM/YYYY): {new_format}")
    print(f"Expected in URL: date={new_format}")
    print(f"Expected in form: pred-date = '{new_format}'")
    
    # Verify format is correct
    expected = "02/11/2025"
    if new_format == expected:
        print(f"✅ Date format is correct: {new_format}")
        return True
    else:
        print(f"❌ Date format is wrong: expected {expected}, got {new_format}")
        return False

def check_findtargets_code():
    """Check that the findTargets.py code has been updated correctly"""
    print("\n🔍 Checking findTargets.py Code")
    print("-" * 40)
    
    try:
        findtargets_path = Path("nina_scheduling/findTargets.py")
        if not findtargets_path.exists():
            print("❌ findTargets.py not found")
            return False
            
        with open(findtargets_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for the updated date format in URL
        if "date={obs_date.strftime('%d/%m/%Y')}" in content:
            print("✅ URL parameter uses DD/MM/YYYY format")
            url_ok = True
        else:
            print("❌ URL parameter not updated to DD/MM/YYYY")
            url_ok = False
        
        # Check for the updated date format in JavaScript
        if "target_date = obs_date.strftime('%d/%m/%Y')" in content:
            print("✅ JavaScript date setting uses DD/MM/YYYY format")
            js_ok = True
        else:
            print("❌ JavaScript date setting not updated to DD/MM/YYYY")
            js_ok = False
        
        # Check for the correct logging
        if "(DD/MM/YYYY format)" in content:
            print("✅ Enhanced logging includes format indicator")
            log_ok = True
        else:
            print("❌ Enhanced logging not found")
            log_ok = False
        
        return url_ok and js_ok and log_ok
        
    except Exception as e:
        print(f"❌ Error checking findTargets.py: {e}")
        return False

def check_cache_files():
    """Check for cache files and analyze their contents"""
    print("\n📁 Checking Cache Files")
    print("-" * 40)
    
    cache_dir = Path("nina_scheduling")
    cache_files = list(cache_dir.glob("cache_raw_targets_*.json"))
    
    if not cache_files:
        print("ℹ️  No cache files found (this is expected for a fresh test)")
        print("   Run the GUI and generate targets to create cache files")
        return None
    
    # Find the most recent cache file
    latest_cache = max(cache_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Found cache file: {latest_cache.name}")
    
    try:
        with open(latest_cache, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            print("⚠️  Cache file is empty")
            return False
        
        print(f"📊 Cache contains {len(data)} targets")
        
        # Analyze the dates in the targets
        date_counts = {}
        sample_targets = []
        
        for target in data[:10]:  # Sample first 10 targets
            minima_time = target.get('minimum_time', '')
            name = target.get('name', 'Unknown')
            
            if minima_time:
                date_part = minima_time.split(',')[0].strip()
                date_counts[date_part] = date_counts.get(date_part, 0) + 1
                sample_targets.append(f"{name}: {minima_time}")
        
        print("\n🎯 Sample targets:")
        for target in sample_targets[:5]:
            print(f"   {target}")
        
        print(f"\n📅 Date distribution:")
        for date_str, count in sorted(date_counts.items()):
            print(f"   {date_str}: {count} targets")
        
        # Check if we got the correct date
        today_str = "11/02/25"  # November 2, 2025 in MM/DD/YY format
        yesterday_str = "11/01/25"  # November 1, 2025
        
        if today_str in date_counts:
            print(f"\n✅ SUCCESS: Found {date_counts[today_str]} targets for today ({today_str})")
            return True
        elif yesterday_str in date_counts:
            print(f"\n❌ FAILURE: Found {date_counts[yesterday_str]} targets for yesterday ({yesterday_str})")
            print("   The date format fix is not working - still getting yesterday's data")
            return False
        else:
            print(f"\n⚠️  UNEXPECTED: Found targets for other dates")
            print("   Check if the date format or timezone logic needs adjustment")
            return False
            
    except Exception as e:
        print(f"❌ Error reading cache file: {e}")
        return False

def test_gui_components():
    """Test that GUI components are properly set up"""
    print("\n🖥️  Checking GUI Components")
    print("-" * 40)
    
    try:
        gui_path = Path("nina_scheduling/target_selector_gui.py")
        if not gui_path.exists():
            print("❌ target_selector_gui.py not found")
            return False
            
        with open(gui_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for Clear Cache button
        if "Clear Cache" in content:
            print("✅ Clear Cache button found in GUI")
            cache_btn_ok = True
        else:
            print("❌ Clear Cache button not found")
            cache_btn_ok = False
        
        # Check for config system
        if "config.py" in content or "update_config_from_gui_values" in content:
            print("✅ Persistent configuration system integrated")
            config_ok = True
        else:
            print("❌ Configuration system not integrated")
            config_ok = False
        
        return cache_btn_ok and config_ok
        
    except Exception as e:
        print(f"❌ Error checking GUI: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("  TESTING DD/MM/YYYY DATE FORMAT FIX")
    print("=" * 60)
    
    # Run all tests
    format_ok = test_date_format_logic()
    code_ok = check_findtargets_code()
    cache_result = check_cache_files()  # Can be None, True, or False
    gui_ok = test_gui_components()
    
    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    print(f"📅 Date Format Logic:     {'✅ PASS' if format_ok else '❌ FAIL'}")
    print(f"🔧 Code Implementation:   {'✅ PASS' if code_ok else '❌ FAIL'}")
    print(f"🖥️  GUI Components:       {'✅ PASS' if gui_ok else '❌ FAIL'}")
    
    if cache_result is None:
        print(f"📁 Cache File Analysis:   ℹ️  NO DATA (run GUI to test)")
    elif cache_result:
        print(f"📁 Cache File Analysis:   ✅ PASS (correct dates found)")
    else:
        print(f"📁 Cache File Analysis:   ❌ FAIL (wrong dates found)")
    
    # Overall result
    tests_passed = sum([format_ok, code_ok, gui_ok])
    total_tests = 3
    
    if cache_result is True:
        tests_passed += 1
        total_tests += 1
    elif cache_result is False:
        total_tests += 1
    
    print(f"\nOverall: {tests_passed}/{total_tests} tests passed")
    
    if cache_result is None:
        print("\n💡 To complete testing:")
        print("   1. Run the GUI: cmd /c venv\\Scripts\\python.exe target_selector_gui.py")
        print("   2. Click 'Clear Cache' to remove old data")
        print("   3. Click 'Generate Targets' to fetch new data")
        print("   4. Run this test again to verify results")
    elif cache_result is False:
        print("\n🔧 The date format fix needs more investigation")
        print("   Check the selenium logs for date setting confirmation")
    elif tests_passed == total_tests:
        print("\n🎉 All tests passed! The date format fix is working correctly!")

if __name__ == "__main__":
    # Change to the correct directory
    os.chdir(Path(__file__).parent)
    main()