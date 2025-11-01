#!/usr/bin/env pwsh
# run_nina_scheduler_test.ps1
# PowerShell script to run the NINA scheduler API test

Write-Host "?? obsybox NINA Scheduler API Test" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "? Python not found in PATH" -ForegroundColor Red
    Write-Host "   Please ensure Python is installed and accessible" -ForegroundColor Yellow
    exit 1
}

# Check if NINA is running (try to connect to API)
Write-Host "?? Checking if NINA is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:1888/v2/api/version" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "? NINA API is accessible" -ForegroundColor Green
} catch {
  Write-Host "? Cannot connect to NINA API at http://localhost:1888" -ForegroundColor Red
 Write-Host "   Please ensure:" -ForegroundColor Yellow
    Write-Host "   1. NINA is running" -ForegroundColor Yellow
    Write-Host "   2. API is enabled in NINA settings" -ForegroundColor Yellow
    Write-Host "   3. Port 1888 is not blocked by firewall" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
   exit 1
    }
}

# Check if Ground Station plugin is available (optional)
Write-Host "?? Checking Ground Station plugin..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:1888/v2/api/plugins" -TimeoutSec 5 -ErrorAction SilentlyContinue
    # Note: We can't easily check plugin list without knowing exact endpoint
    Write-Host "??  Plugin check skipped - will test during execution" -ForegroundColor Blue
} catch {
    Write-Host "??  Could not check plugins - will test during execution" -ForegroundColor Blue
}

# Run the test
Write-Host "?? Starting scheduler test..." -ForegroundColor Green
Write-Host ""

try {
    # Change to the script directory
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Push-Location $scriptDir
    
    # Run the Python test script
    python test_nina_scheduler_api.py
 
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "?? Test completed successfully!" -ForegroundColor Green
   Write-Host "   Check your Pushover notifications for test messages" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "? Test failed with exit code $exitCode" -ForegroundColor Red
    }
    
} catch {
    Write-Host "?? Error running test: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "?? Test Notes:" -ForegroundColor Cyan
Write-Host "   - This test only sends notifications (no hardware movement)" -ForegroundColor White
Write-Host "   - Check NINA's log for any API errors" -ForegroundColor White
Write-Host "   - Modify test_config.json to customize test parameters" -ForegroundColor White

exit $exitCode