param(
    [string]$Drive = 'C:'
)

# Gather CPU load (average across processors)
$cpuLoad = $null
try {
    $cpuObjs = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue
    if ($cpuObjs) {
        $avg = ($cpuObjs | Measure-Object -Property LoadPercentage -Average).Average
        if ($avg -ne $null) { $cpuLoad = [math]::Round($avg,1) }
    }
} catch { $cpuLoad = $null }

# Gather CPU temperature via WMI (MSAcpi_ThermalZoneTemperature). May be unavailable on many systems.
$cpuTemp = $null
try {
    $tempObjs = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue
    if ($tempObjs) {
        # CurrentTemperature is tenths of Kelvin
        $tempsC = $tempObjs | ForEach-Object { ($_.CurrentTemperature/10) - 273.15 }
        if ($tempsC -and $tempsC.Count -ge 1) { $cpuTemp = [math]::Round($tempsC[0],1) }
    }
} catch { $cpuTemp = $null }

# Disk free/total for selected drive
$freeGB = $null; $totalGB = $null
try {
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$Drive'" -ErrorAction SilentlyContinue
    if ($disk) { $freeGB = [math]::Round($disk.FreeSpace/1GB,2); $totalGB = [math]::Round($disk.Size/1GB,2) }
} catch { $freeGB = $null; $totalGB = $null }

# Wi-Fi: read Signal percent via netsh and estimate dBm using a simple conversion (dBm ≈ (percent/2) - 100).
$signalPercent = $null; $signalDbm = $null
try {
    $interfacesText = (& netsh wlan show interfaces) 2>$null
    if ($interfacesText) {
        $signalLine = ($interfacesText -split "`r?`n" | Where-Object { $_ -match '^\s*Signal' })[0]
        if ($signalLine) {
            $raw = ($signalLine -split ':')[1].Trim()
            $raw = $raw.TrimEnd('%')
            if ($raw -match '^\d+$') { $signalPercent = [int]$raw; $signalDbm = [math]::Round(($signalPercent/2) - 100,0) }
        }
    }
} catch { }

# Build ordered result and print JSON
$result = [ordered]@{
    machine_name = $env:COMPUTERNAME
    cpu_temp_c = $cpuTemp
    cpu_load_percent = $cpuLoad
    disk_free_gb = $freeGB
    disk_total_gb = $totalGB
    wifi_signal_percent = $signalPercent
    wifi_signal_dbm = $signalDbm
}

# Remove keys with $null values
$filtered = [ordered]@{}
foreach ($k in $result.Keys) {
    $v = $result[$k]
    if ($null -ne $v) { $filtered[$k] = $v }
}

$json = $filtered | ConvertTo-Json -Compress

# Try to publish via Python/paho.mqtt if available; otherwise print JSON to stdout.
$tempFile = [IO.Path]::Combine($env:TEMP, ([guid]::NewGuid().ToString() + '.json'))
try {
    Set-Content -Path $tempFile -Value $json -Encoding UTF8
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        try {
            & $pythonCmd.Path -c "import sys, paho.mqtt.publish as publish; publish.single('obsybox/system_monitoring', open(sys.argv[1],'rb').read(), hostname='192.168.1.49')" $tempFile
            Write-Output "Published to MQTT topic obsybox/system_monitoring via Python"
        } catch {
            Write-Warning "Python publish failed: $_"
            Write-Output $json
        }
    } else {
        # Optionally try mosquitto_pub if available
        $mosq = Get-Command mosquitto_pub -ErrorAction SilentlyContinue
        if ($mosq) {
            try {
                & $mosq.Path -h 192.168.1.49 -t obsybox/system_monitoring -f $tempFile
                Write-Output "Published to MQTT topic obsybox/system_monitoring via mosquitto_pub"
            } catch {
                Write-Warning "mosquitto_pub publish failed: $_"
                Write-Output $json
            }
        } else {
            # No publisher available; print JSON
            Write-Output $json
        }
    }
} finally {
    if (Test-Path $tempFile) { Remove-Item -Path $tempFile -ErrorAction SilentlyContinue }
}
