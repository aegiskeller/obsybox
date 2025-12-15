#!/usr/bin/env pwsh
# Run scan_data_dirs.py and capture all output to calibration_full_log.txt

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pythonExe = Join-Path $scriptDir "venv\Scripts\python.exe"

# Run Python script and redirect stdout/stderr to file
& $pythonExe scan_data_dirs.py --dry-run 2>&1 | Out-File -FilePath calibration_full_log.txt -Encoding UTF8

Write-Host "Scan complete. Output saved to calibration_full_log.txt"
Write-Host "File size: $((Get-Item calibration_full_log.txt).Length) bytes"
