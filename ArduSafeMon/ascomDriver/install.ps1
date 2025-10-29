# Installation script for ArduSafeMon ASCOM Driver
# Must be run as Administrator

param(
    [switch]$Uninstall
)

# Check for Administrator privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$dllPath = Join-Path $PSScriptRoot "bin\Release\net48\ASCOM.ArduSafeMon.SafetyMonitor.dll"

if (-not (Test-Path $dllPath)) {
    Write-Host "ERROR: DLL not found at: $dllPath" -ForegroundColor Red
    Write-Host "Please build the project first using build.ps1" -ForegroundColor Yellow
    exit 1
}

if ($Uninstall) {
    Write-Host "Uninstalling ArduSafeMon ASCOM Driver..." -ForegroundColor Cyan
    & regasm /unregister "$dllPath"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Driver uninstalled successfully!" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Failed to uninstall driver" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Installing ArduSafeMon ASCOM Driver..." -ForegroundColor Cyan
    & regasm /codebase "$dllPath"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=======================================" -ForegroundColor Green
        Write-Host "Driver installed successfully!" -ForegroundColor Green
        Write-Host "=======================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Open ASCOM Device Chooser" -ForegroundColor White
        Write-Host "2. Select 'ArduSafeMon Safety Monitor'" -ForegroundColor White
        Write-Host "3. Click 'Properties' to configure COM port" -ForegroundColor White
        Write-Host "4. Test with NINA or ASCOM Diagnostics" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "ERROR: Failed to install driver" -ForegroundColor Red
        Write-Host "Make sure ASCOM Platform 6.6+ is installed" -ForegroundColor Yellow
        exit 1
    }
}
