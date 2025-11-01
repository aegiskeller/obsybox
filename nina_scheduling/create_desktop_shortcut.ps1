# PowerShell script to create a desktop shortcut for NINA Target Selector GUI

# Get the current user's desktop path
$DesktopPath = [Environment]::GetFolderPath("Desktop")

# Define the shortcut properties
$ShortcutName = "NINA Target Selector"
$ShortcutPath = Join-Path $DesktopPath "$ShortcutName.lnk"
$TargetPath = "C:\Users\aegis\Documents\obsybox\nina_scheduling\run_target_gui.bat"
$WorkingDirectory = "C:\Users\aegis\Documents\obsybox\nina_scheduling"
$Description = "NINA Target Selector GUI for Eclipsing Binary Star Scheduling"

# Create the WScript.Shell COM object
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
} else {
    # Fall back to default batch file icon
    $Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,153"
}

# Save the shortcut
$Shortcut.Save()

# Check if the shortcut was created successfully
if (Test-Path $ShortcutPath) {
    Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
    Write-Host "Location: $ShortcutPath" -ForegroundColor Cyan
    Write-Host "You can now double-click 'NINA Target Selector' on your desktop to launch the GUI" -ForegroundColor Yellow
} else {
    Write-Host "Failed to create desktop shortcut" -ForegroundColor Red
}

Write-Host ""
Write-Host "Setup complete! You can launch the GUI by:" -ForegroundColor Green
Write-Host "  - Double-clicking the desktop icon" -ForegroundColor White
Write-Host "  - Running the batch file: run_target_gui.bat" -ForegroundColor White