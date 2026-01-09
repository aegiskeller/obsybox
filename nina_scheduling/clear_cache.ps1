# Clear all cached target files to force regeneration with coordinate enrichment

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Clear Target Cache Files" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$cacheFiles = Get-ChildItem -Path . -Filter "cache_raw_targets_*.json"

if ($cacheFiles.Count -eq 0) {
    Write-Host "No cache files found." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

Write-Host "Found $($cacheFiles.Count) cache file(s):" -ForegroundColor White
foreach ($file in $cacheFiles) {
    Write-Host "  - $($file.Name)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "These files will be deleted and regenerated with coordinate enrichment." -ForegroundColor Yellow
$confirm = Read-Host "Continue? (y/n)"

if ($confirm -ne 'y') {
    Write-Host "Cancelled." -ForegroundColor Red
    exit 1
}

Write-Host ""
foreach ($file in $cacheFiles) {
    Remove-Item $file.FullName -Force
    Write-Host "Deleted: $($file.Name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Cache cleared successfully!" -ForegroundColor Green
Write-Host "Next time you fetch targets, coordinates will be automatically resolved." -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
