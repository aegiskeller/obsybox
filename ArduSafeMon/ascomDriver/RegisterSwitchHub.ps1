# RegisterSwitchHub.ps1
# Registers the Wombat Switch Hub in the ASCOM Profile

Write-Host "Registering Wombat Switch Hub in ASCOM Profile..." -ForegroundColor Cyan

try {
    $ascomProfile = New-Object -ComObject "ASCOM.Utilities.Profile"
    $ascomProfile.DeviceType = "Switch"
    $ascomProfile.Register("ASCOM.ArduSafeMon.SwitchHub", "Wombat Switch Hub (All Sensors)")
    Write-Host "Successfully registered Wombat Switch Hub!" -ForegroundColor Green
}
catch {
    Write-Host "Error registering Switch Hub: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Registration complete. The Switch Hub should now appear in ASCOM device choosers." -ForegroundColor Green
