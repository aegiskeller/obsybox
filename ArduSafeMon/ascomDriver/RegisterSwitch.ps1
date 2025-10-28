# Register the ArduSafeMon Switch driver with ASCOM Profile
# Run this as Administrator after building and registering with regasm

$ErrorActionPreference = "Stop"

Write-Host "Registering ArduSafeMon Switch with ASCOM Profile..." -ForegroundColor Cyan

try {
    # Create ASCOM Profile object
    $ascomProfile = New-Object -ComObject "ASCOM.Utilities.Profile"
    
    # Set device type to Switch
    $ascomProfile.DeviceType = "Switch"
    
    # Register the driver
    $driverID = "ASCOM.ArduSafeMon.Switch"
    $description = "ArduSafeMon Switch (Sensor Values)"
    
    Write-Host "Registering: $driverID" -ForegroundColor Yellow
    $ascomProfile.Register($driverID, $description)
    
    Write-Host "Successfully registered ArduSafeMon Switch!" -ForegroundColor Green
    Write-Host "Device should now appear in ASCOM Switch choosers." -ForegroundColor Green
    
    # Release COM object
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($ascomProfile) | Out-Null
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Make sure:" -ForegroundColor Yellow
    Write-Host "  1. ASCOM Platform is installed" -ForegroundColor Yellow
    Write-Host "  2. You ran regasm on the DLL first" -ForegroundColor Yellow
    Write-Host "  3. You're running this as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
