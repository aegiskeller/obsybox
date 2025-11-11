param(
    [int]$IntervalSeconds = 300
)

# Wrapper that repeatedly runs the existing run_get_system_stats.cmd script
# Place this file in the same folder as run_get_system_stats.cmd and schedule
# this PowerShell script to run at startup (once). It will loop forever and
# run the .cmd every $IntervalSeconds seconds.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CmdPath = Join-Path $ScriptDir 'run_get_system_stats.cmd'
$LogFile = 'C:\Logs\obsybox\get_system_stats.log'

if (-not (Test-Path $CmdPath)) {
    Add-Content -Path $LogFile -Value ("[{0}] ERROR: wrapper cannot find {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $CmdPath)
    throw "Cannot find $CmdPath"
}

Add-Content -Path $LogFile -Value ("[{0}] wrapper started, interval={1}s" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $IntervalSeconds)

while ($true) {
    try {
        & "$CmdPath"
    } catch {
        # Log and continue looping
        $msg = $_.Exception.Message -replace "\r|\n", ' '
        Add-Content -Path $LogFile -Value ("[{0}] wrapper exception: {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg)
    }

    Start-Sleep -Seconds $IntervalSeconds
}
