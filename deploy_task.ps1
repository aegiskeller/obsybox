<#
deploy_task.ps1

Creates `run_get_system_stats.cmd` (or updates it) and registers a scheduled task that runs every minute.

Usage (run PowerShell as Administrator):
    .\deploy_task.ps1 -PythonPath 'C:\Path\To\python.exe' -RunAsUser 'SYSTEM'

If -PythonPath is omitted the script will try to find `python` on PATH.
#>

param(
    [string]$PythonPath,
    [string]$ScriptPath = "$PSScriptRoot\systemMonitoring\ComputeMonitoring\get_system_stats.py",
    [string]$WrapperPath = "$PSScriptRoot\run_get_system_stats.cmd",
    [string]$LogDir = "C:\Logs\obsybox",
    [string]$TaskName = "Obsybox_GetSystemStats",
    [string]$RunAsUser = "SYSTEM"
)

Write-Host "Deploying scheduled task: $TaskName"

# Resolve Python path if not provided
if (-not $PythonPath) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $PythonPath = $cmd.Source }
}

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 2
}

# Ensure log directory exists
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# Build wrapper content
$content = "@echo off`r`n"
if ($PythonPath) {
    $p = $PythonPath.Replace('"','')
    $s = $ScriptPath.Replace('"','')
    $l = Join-Path $LogDir 'get_system_stats.log'
    $content += "`"$p`" `"$s`" D: >> `"$l`" 2>&1`r`n"
} else {
    # fallback to python on PATH
    $s = $ScriptPath.Replace('"','')
    $l = Join-Path $LogDir 'get_system_stats.log'
    $content += "python `"$s`" D: >> `"$l`" 2>&1`r`n"
}

Write-Host "Writing wrapper to $WrapperPath"
Set-Content -Path $WrapperPath -Value $content -Encoding ASCII -Force

Write-Host "Wrapper created. Registering scheduled task..."

# Build schtasks args
$args = @('/Create','/SC','MINUTE','/MO','1','/TN',$TaskName,'/TR',$WrapperPath,'/ST','00:00','/DU','24:00','/F','/RL','HIGHEST','/RU',$RunAsUser)

Write-Host "Running: schtasks $($args -join ' ')"
$proc = Start-Process -FilePath schtasks -ArgumentList $args -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -eq 0) {
    Write-Host "Scheduled task registered successfully."
    Write-Host "To run now: schtasks /Run /TN `"$TaskName`""
    Write-Host "To delete: schtasks /Delete /TN `"$TaskName`" /F"
} else {
    Write-Warning "schtasks returned exit code $($proc.ExitCode). Check output above for details."
}

Write-Host "Done. Log file: $LogDir\get_system_stats.log"
