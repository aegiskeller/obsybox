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

Write-Host "This deploy script has moved. Use systemMonitoring\ComputeMonitoring\deploy_task.ps1 instead."
Write-Host "To run the local deploy script from the repo root:" 
Write-Host ".\systemMonitoring\ComputeMonitoring\deploy_task.ps1 -PythonPath 'C:\Path\To\python.exe'"
exit 0
 
