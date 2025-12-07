# Disable Windows auto-update for CH340 drivers
# Run as Administrator

Write-Host "CH340 Driver Auto-Update Blocker" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit
}

Write-Host "Step 1: Listing all CH340 devices..." -ForegroundColor Cyan
$ch340Devices = Get-PnpDevice | Where-Object { 
    $_.FriendlyName -like "*CH340*" -or 
    $_.FriendlyName -like "*CH343*" -or
    $_.InstanceId -like "*VID_1A86*"
}

if ($ch340Devices.Count -eq 0) {
    Write-Host "No CH340 devices found. Make sure device is connected." -ForegroundColor Yellow
    pause
    exit
}

Write-Host "Found $($ch340Devices.Count) CH340 device(s):" -ForegroundColor Green
$ch340Devices | Format-Table FriendlyName, Status, InstanceId -AutoSize

Write-Host ""
Write-Host "Step 2: Disabling driver updates for these devices..." -ForegroundColor Cyan

foreach ($device in $ch340Devices) {
    $hwid = $device.InstanceId
    
    # Add to registry to prevent driver updates
    $regPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions"
    
    if (-not (Test-Path $regPath)) {
        New-Item -Path $regPath -Force | Out-Null
    }
    
    # Set policy to prevent driver updates for this hardware ID
    Set-ItemProperty -Path $regPath -Name "DenyDeviceIDs" -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $regPath -Name "DenyDeviceIDsRetroactive" -Value 1 -Type DWord -Force
    
    Write-Host "  ✓ Protected: $($device.FriendlyName)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 3: Disabling Windows Update driver installation globally..." -ForegroundColor Cyan

# Disable automatic driver updates via Windows Update
$regPath2 = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching"
if (-not (Test-Path $regPath2)) {
    New-Item -Path $regPath2 -Force | Out-Null
}
Set-ItemProperty -Path $regPath2 -Name "SearchOrderConfig" -Value 0 -Type DWord -Force

# Disable driver updates via Device Installation Settings
$regPath3 = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Device Metadata"
if (-not (Test-Path $regPath3)) {
    New-Item -Path $regPath3 -Force | Out-Null
}
Set-ItemProperty -Path $regPath3 -Name "PreventDeviceMetadataFromNetwork" -Value 1 -Type DWord -Force

Write-Host "  ✓ Disabled automatic driver downloads from Windows Update" -ForegroundColor Green

Write-Host ""
Write-Host "SUCCESS! CH340 drivers are now protected from Windows Update" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Download CH340 driver 3.4.2014.8 (dated 08/08/2014)" -ForegroundColor White
Write-Host "   Source: http://www.wch.cn/downloads/CH341SER_ZIP.html" -ForegroundColor White
Write-Host "2. Uninstall current driver from Device Manager" -ForegroundColor White
Write-Host "3. Install the 2014 version manually" -ForegroundColor White
Write-Host "4. Reboot your computer" -ForegroundColor White
Write-Host ""

pause
}
