#!/usr/bin/env python3
"""
Test script to verify GUI wait detection functionality
"""

import tempfile
import os
from datetime import datetime
from pathlib import Path

# Create a test NINA log with wait state
def create_test_log_with_wait():
    """Create a temporary NINA log file with wait state for testing"""
    
    now = datetime.now()
    start_time = now.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Create log content with active wait
    log_content = f"""{start_time}.0157|INFO|SequenceItem.cs|Run|208|Starting Category: Utility, Item: WaitForTime, Time: 20:30:00h, Offset: 10
{start_time}.0200|INFO|Other|Normal activity
"""
    
    # Write to a temporary file in the expected NINA log location
    test_log_dir = Path("C:/Users/aegis/AppData/Local/NINA/Logs")
    test_log_dir.mkdir(parents=True, exist_ok=True)
    
    test_log_file = test_log_dir / f"nina-test-{datetime.now().strftime('%Y%m%d')}.log"
    
    with open(test_log_file, 'w') as f:
        f.write(log_content)
    
    print(f"Created test log file: {test_log_file}")
    print(f"Content:\n{log_content}")
    print("\nThe GUI should now detect this as a wait state and show 'WAIT' status.")
    print("Press Enter to remove the test file and return to normal monitoring...")
    
    input()
    
    # Clean up
    try:
        os.unlink(test_log_file)
        print(f"Removed test file: {test_log_file}")
    except:
        print(f"Could not remove test file: {test_log_file}")

if __name__ == "__main__":
    create_test_log_with_wait()