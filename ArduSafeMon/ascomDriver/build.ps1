# PowerShell build script for ArduSafeMon ASCOM Driver
# Can be run directly from PowerShell

Write-Host "Building ArduSafeMon ASCOM SafetyMonitor Driver..." -ForegroundColor Cyan
Write-Host ""

# Check for .NET SDK
try {
    $dotnetVersion = dotnet --version
    Write-Host "Found .NET SDK version: $dotnetVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: .NET SDK not found!" -ForegroundColor Red
    Write-Host "Install from: https://dotnet.microsoft.com/download/dotnet-framework" -ForegroundColor Yellow
    exit 1
}

# Build the project
Write-Host ""
Write-Host "Building Release configuration..." -ForegroundColor Cyan
dotnet build ArduSafeMon.csproj -c Release

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Output location: bin\Release\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To install the driver:" -ForegroundColor Cyan
    Write-Host "1. Open PowerShell as Administrator" -ForegroundColor White
    Write-Host "2. Navigate to bin\Release\" -ForegroundColor White
    Write-Host "3. Run: regasm /codebase ASCOM.ArduSafeMon.SafetyMonitor.dll" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: Build failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    exit 1
}
