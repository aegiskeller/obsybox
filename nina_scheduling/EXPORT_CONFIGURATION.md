# NINA Export Directory Configuration

The NINA Target Selector now supports configurable export directories for better organization and flexibility.

## Default Export Location

By default, NINA JSON files are exported to:
```
C:\Users\aegis\Documents\N.I.N.A\Targets\VarStars\YYYYmmdd\
```

Where `YYYYmmdd` is the current date (e.g., `20241102` for November 2, 2024).

## Customizing the Export Directory

To change the export location, create or edit the `user_config.json` file in the `nina_scheduling` directory:

```json
{
  "export_settings": {
    "nina_export_base_dir": "C:\\Your\\Custom\\Path\\To\\Targets"
  }
}
```

### Examples

**Example 1: Different NINA installation**
```json
{
  "export_settings": {
    "nina_export_base_dir": "D:\\NINA\\Targets\\Variables"
  }
}
```

**Example 2: Network storage**
```json
{
  "export_settings": {
    "nina_export_base_dir": "\\\\server\\nina\\targets\\eclipsing"
  }
}
```

**Example 3: Organized by observer**
```json
{
  "export_settings": {
    "nina_export_base_dir": "C:\\Astronomy\\Observations\\VarStars"
  }
}
```

## How It Works

1. The system reads the configuration from `user_config.json` when starting
2. If no custom path is set, uses the default NINA location
3. Creates a dated subdirectory (YYYYmmdd format) for each observation session
4. Both the GUI and command-line tools use the same configuration

## Path Format Notes

- Use double backslashes (`\\`) in JSON for Windows paths
- Forward slashes (`/`) also work: `"C:/Users/aegis/Documents/NINA/Targets"`
- Raw strings work in Python: `r"C:\Users\aegis\Documents\NINA\Targets"`
- The date subdirectory is automatically created and organized by observation date

## Configuration File Location

The `user_config.json` file should be placed in the same directory as the Python scripts:
```
nina_scheduling/
├── findTargets.py
├── target_selector_gui.py
├── user_config.json        ← Create this file
└── ...
```

## Backup Recommendation

Since NINA sequences are valuable, consider:
1. Using a path that's backed up regularly
2. Setting up NINA's own backup/export features
3. Version controlling your observation templates and configurations