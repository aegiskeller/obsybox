# PowerShell script to create a desktop shortcut for NINA Target Selector GUI
# Updated with better error handling and icon management

# Get the current user's desktop path
$DesktopPath = [Environment]::GetFolderPath("Desktop")

# Define the shortcut properties
$ShortcutName = "NINA Target Selector"
$ShortcutPath = Join-Path $DesktopPath "$ShortcutName.lnk"
$TargetPath = "C:\Users\aegis\Documents\obsybox\nina_scheduling\run_target_gui.bat"
$WorkingDirectory = "C:\Users\aegis\Documents\obsybox\nina_scheduling"
$Description = "NINA Target Selector GUI for Eclipsing Binary Star Scheduling with Persistent Configuration"

Write-Host "Creating desktop shortcut for NINA Target Selector..." -ForegroundColor Yellow

# Verify the target batch file exists
if (-not (Test-Path $TargetPath)) {
    Write-Host "ERROR: Target batch file not found at: $TargetPath" -ForegroundColor Red
    Write-Host "Please ensure run_target_gui.bat exists in the nina_scheduling directory" -ForegroundColor Red
    exit 1
}

# Create the WScript.Shell COM object
try {
    $WshShell = New-Object -ComObject WScript.Shell
    
    # Create the shortcut
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $TargetPath
    $Shortcut.WorkingDirectory = $WorkingDirectory
    $Shortcut.Description = $Description
    $Shortcut.WindowStyle = 1  # Normal window
    
    # Try to set an icon (using Python icon from the virtual environment)
    $PythonIconPath = "C:\Users\aegis\Documents\obsybox\nina_scheduling\venv\Scripts\python.exe"
    if (Test-Path $PythonIconPath) {
        $Shortcut.IconLocation = "$PythonIconPath,0"
        Write-Host "Using Python icon from virtual environment" -ForegroundColor Cyan
    } else {
        # Fall back to a telescope/astronomy-themed icon
        $Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,42"  # World/globe icon
        Write-Host "Using default system icon (Python venv not found)" -ForegroundColor Yellow
    }
    
    # Save the shortcut
    $Shortcut.Save()
    
    # Verify creation
    if (Test-Path $ShortcutPath) {
        Write-Host ""
        Write-Host "SUCCESS: Desktop shortcut created!" -ForegroundColor Green
        Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Features of this updated launcher:" -ForegroundColor Yellow
        Write-Host "  * Enhanced error handling and diagnostics" -ForegroundColor White
        Write-Host "  * Persistent configuration storage" -ForegroundColor White
        Write-Host "  * Timezone-aware observation night calculation" -ForegroundColor White
        Write-Host "  * Automatic cache management" -ForegroundColor White
        Write-Host "  * Reset to defaults functionality" -ForegroundColor White
        Write-Host ""
        Write-Host "You can now double-click 'NINA Target Selector' on your desktop!" -ForegroundColor Green
    } else {
        throw "Shortcut file was not created"
    }
    
} catch {
    Write-Host "ERROR: Failed to create desktop shortcut" -ForegroundColor Red
    Write-Host "Details: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "You can still run the GUI manually using:" -ForegroundColor Yellow
    Write-Host "  $TargetPath" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Setup complete! Launch options:" -ForegroundColor Green
Write-Host "  1. Double-click the desktop icon: 'NINA Target Selector'" -ForegroundColor White
Write-Host "  2. Run the batch file: run_target_gui.bat" -ForegroundColor White
Write-Host "  3. Command line: venv\Scripts\python.exe target_selector_gui.py" -ForegroundColor White
Write-Host ""
Write-Host "TIP: The GUI now automatically saves your parameter preferences!" -ForegroundColor Cyan