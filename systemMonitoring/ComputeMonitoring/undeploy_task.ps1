# undeploy_task.ps1
# Remove Obsybox system monitoring scheduled task

param(
    [switch]$RemoveLog
)

Write-Host "🗑️ Obsybox System Monitoring Task Removal" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "⚠️ This script requires Administrator privileges" -ForegroundColor Red
    Write-Host "   Please run PowerShell as Administrator and try again" -ForegroundColor Yellow
    exit 1
}

$taskName = "Obsybox_GetSystemStats"
$logFile = "C:\Logs\obsybox\get_system_stats.log"

# Check if task exists
try {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "🛑 Stopping task if running..." -ForegroundColor Yellow
        try {
            Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        } catch {
            # Task wasn't running, continue
        }
        
        Write-Host "🗑️ Removing scheduled task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "✅ Task '$taskName' removed successfully!" -ForegroundColor Green
    } else {
        Write-Host "ℹ️ Task '$taskName' does not exist" -ForegroundColor Blue
    }
} catch {
    Write-Host "❌ Error removing task: $_" -ForegroundColor Red
    exit 1
}

# Remove log file if requested
if ($RemoveLog) {
    if (Test-Path $logFile) {
        Write-Host "🗑️ Removing log file..." -ForegroundColor Yellow
        Remove-Item $logFile -Force
        Write-Host "✅ Log file removed: $logFile" -ForegroundColor Green
    } else {
        Write-Host "ℹ️ Log file does not exist: $logFile" -ForegroundColor Blue
    }
}

Write-Host ""
Write-Host "✅ Undeployment complete!" -ForegroundColor Green