#!/usr/bin/env python3
"""
Enhanced NINA sequence generator that integrates with obsybox target selection
"""
import json
import sys
import os
from pathlib import Path

# Add your nina_scheduling path
sys.path.append(str(Path(__file__).parent.parent.parent / "nina_scheduling"))

def generate_sequences_from_obsybox():
    """Generate NINA sequences from your current obsybox target database"""
    try:
        # Import your existing target selection system
        from observation_db import get_tonight_targets
        
        # Get tonight's targets
        targets = get_tonight_targets()
    
        # Convert to NINA format and generate sequences
        output_dir = Path("generated_sequences")
        output_dir.mkdir(exist_ok=True)
        
        template_path = Path("nina_template.json")
        
 for target in targets:
         nina_target = {
 "TARGET_NAME": target["target_name"],
"RAHours": target["ra_hours"],
    "RAMinutes": target["ra_minutes"], 
    "RASeconds": target["ra_seconds"],
"NegativeDec": target["dec_negative"],
         "DecDegrees": target["dec_degrees"],
 "DecMinutes": target["dec_minutes"],
    "DecSeconds": target["dec_seconds"],
         "ExposureTime": target.get("exposure_time", 180),
         "Iterations": target.get("iterations", 20)
         }
   
# Generate sequence file
    sequence_path = output_dir / f"{target['target_name']}.json"
            generate_sequence_file(nina_target, template_path, sequence_path)
   
        print(f"Generated {len(targets)} sequences in {output_dir}")
        
    except ImportError:
        print("Could not import obsybox target system. Using standalone mode.")
    return False
    
    return True

def generate_sequence_file(target_data, template_path, output_path):
    """Generate a single NINA sequence file"""
    with open(template_path, 'r') as f:
        template = f.read()
    
    # Replace placeholders
    for key, value in target_data.items():
   placeholder = f"{{{{{key}}}}}"
        template = template.replace(placeholder, str(value))
    
    # Write output
    with open(output_path, 'w') as f:
        f.write(template)

if __name__ == "__main__":
    if not generate_sequences_from_obsybox():
        print("Run this from your obsybox directory with target database access")