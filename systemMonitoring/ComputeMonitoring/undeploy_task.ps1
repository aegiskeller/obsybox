<#
undeploy_task.ps1

Stops and removes the scheduled task created by deploy_task.ps1, removes the local wrapper
and optionally removes the log file.

Usage (run as Administrator):
  .\undeploy_task.ps1 [-TaskName 'Obsybox_GetSystemStats'] [-WrapperPath '.\\run_get_system_stats.cmd'] [-LogDir 'C:\Logs\obsybox'] [-RemoveLog]

This is safe to run multiple times; missing objects are ignored.
#>

param(
    [string]$TaskName = 'Obsybox_GetSystemStats',
    [string]$WrapperPath = "$PSScriptRoot\run_get_system_stats.cmd",
    [string]$LogDir = 'C:\Logs\obsybox',
    [switch]$RemoveLog,
    [switch]$Force
)

function Remove-FileSafe($path) {
    if (Test-Path $path) {
        try {
            Remove-Item -Path $path -Force -ErrorAction Stop
            Write-Host "Removed file: $path"
        } catch {
            $err = $_.Exception.Message
            Write-Warning ("Failed to remove {0}: {1}" -f $path, $err)
        }
    } else {
        Write-Host "Not found (skipping): $path"
    }
}

Write-Host "Undeploying task: $TaskName"

# Stop running instance if present
try {
    Write-Host "Attempting to stop running task (if any)..."
    schtasks /End /TN "$TaskName" 2>$null | Out-Null
} catch {
    # ignore
}

# Delete the scheduled task
try {
    if ($Force) {
        schtasks /Delete /TN "$TaskName" /F 2>$null | Out-Null
    } else {
        schtasks /Delete /TN "$TaskName" /F 2>$null | Out-Null
    }
    Write-Host "Scheduled task deleted (if it existed): $TaskName"
} catch {
    Write-Warning "Could not delete scheduled task: $_"
}

# Also try PowerShell unregister in case task was created that way
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Unregistered scheduled task (PowerShell) if present: $TaskName"
} catch {
    # ignore
}

# Remove the wrapper file (local)
Write-Host "Removing wrapper: $WrapperPath"
Remove-FileSafe -path $WrapperPath

if ($RemoveLog) {
    $logFile = Join-Path $LogDir 'get_system_stats.log'
    Write-Host "Removing log file: $logFile"
    Remove-FileSafe -path $logFile
} else {
    Write-Host "Log removal skipped. Use -RemoveLog to delete $LogDir\get_system_stats.log"
}

Write-Host "Undeploy complete. If Task Scheduler still lists the task, open Task Scheduler and delete it manually."
