# PowerShell script to create a desktop shortcut for Scheduled Target Viewer
# Creates a shortcut to launch the scheduled target viewer GUI

# Get the current user's desktop path
$DesktopPath = [Environment]::GetFolderPath("Desktop")

# Define the shortcut properties
$ShortcutName = "Scheduled Target Viewer"
$ShortcutPath = Join-Path $DesktopPath "$ShortcutName.lnk"
$ScriptDir = "C:\Users\aegis\Documents\obsybox\nina_scheduling"
$PythonExe = Join-Path $ScriptDir "venv\Scripts\python.exe"
$TargetScript = Join-Path $ScriptDir "scheduled_target_viewer.py"
$WorkingDirectory = $ScriptDir
$Description = "Scheduled Target Viewer - Review and update scheduled observation targets"

Write-Host "Creating desktop shortcut for Scheduled Target Viewer..." -ForegroundColor Yellow

# Verify the Python executable exists
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python executable not found at: $PythonExe" -ForegroundColor Red
    Write-Host "Please ensure the virtual environment exists" -ForegroundColor Red
    exit 1
}

# Verify the target script exists
if (-not (Test-Path $TargetScript)) {
    Write-Host "ERROR: Script not found at: $TargetScript" -ForegroundColor Red
    Write-Host "Please ensure scheduled_target_viewer.py exists" -ForegroundColor Red
    exit 1
}

# Create the WScript.Shell COM object
try {
    $WshShell = New-Object -ComObject WScript.Shell
    
    # Create the shortcut
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $PythonExe
    $Shortcut.Arguments = "`"$TargetScript`""
    $Shortcut.WorkingDirectory = $WorkingDirectory
    $Shortcut.Description = $Description
    $Shortcut.WindowStyle = 1  # Normal window
    
    # Set icon (using Python icon from the virtual environment)
    if (Test-Path $PythonExe) {
        $Shortcut.IconLocation = "$PythonExe,0"
        Write-Host "Using Python icon from virtual environment" -ForegroundColor Cyan
    }
    
    # Save the shortcut
    $Shortcut.Save()
    
    # Verify creation
    if (Test-Path $ShortcutPath) {
        Write-Host ""
        Write-Host "SUCCESS! Desktop shortcut created:" -ForegroundColor Green
        Write-Host "  Location: $ShortcutPath" -ForegroundColor Cyan
        Write-Host "  Target: $PythonExe" -ForegroundColor Cyan
        Write-Host "  Script: $TargetScript" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "You can now launch Scheduled Target Viewer from your desktop!" -ForegroundColor Green
    } else {
        throw "Shortcut file was not created"
    }
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create shortcut" -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    exit 1
}

# Release COM object
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($WshShell) | Out-Null
[System.GC]::Collect()
[System.GC]::WaitForPendingFinalizers()

Write-Host "Done!" -ForegroundColor Green
