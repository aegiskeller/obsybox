#!/bin/bash

# Settings
MQTT_BROKER="192.168.1.49"
MQTT_TOPIC="obsybox/system_monitoring"

# Get CPU temperature (in Celsius)
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
  CPUTEMP=$(awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
else
  CPUTEMP=$(vcgencmd measure_temp 2>/dev/null | grep -oP '[0-9.]+')
fi

# Get CPU load percentage (average over 1 second)
CPU_LOAD=$(top -bn2 -d 0.5 | grep "Cpu(s)" | tail -n1 | awk -F',' '{for(i=1;i<=NF;i++){if($i~/%Cpu/){split($i,a,":");cpu=a[2]}else if($i~/%id/){idle=$i}}} END{gsub(/[^0-9.]/,"",idle); print 100-idle}')
if [ -z "$CPU_LOAD" ]; then
  # Fallback: parse /proc/stat (Linux standard, no extra tools)
  PREV_IDLE=$(awk '/^cpu /{print $5}' /proc/stat)
  PREV_TOTAL=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8+$9+$10}' /proc/stat)
  sleep 1
  IDLE=$(awk '/^cpu /{print $5}' /proc/stat)
  TOTAL=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8+$9+$10}' /proc/stat)
  DIFF_IDLE=$((IDLE - PREV_IDLE))
  DIFF_TOTAL=$((TOTAL - PREV_TOTAL))
  if [ "$DIFF_TOTAL" -gt 0 ]; then
    CPU_LOAD=$(awk "BEGIN { printf \"%.1f\", (1-($DIFF_IDLE/$DIFF_TOTAL))*100 }")
  else
    CPU_LOAD="0"
  fi
fi

# Get free disk space on root (in GB)
DISK_FREE=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')

# Get WiFi signal strength (RSSI in dBm)
WIFI_IF=${WIFI_IFACE:-wlan0}
if ip link show "$WIFI_IF" > /dev/null 2>&1; then
  WIFI_SIGNAL=$(iwconfig "$WIFI_IF" 2>/dev/null | grep -i --color=never 'signal level' | awk -F '=' '{print $3}' | awk '{print $1}')
  if [ -z "$WIFI_SIGNAL" ]; then
    WIFI_SIGNAL=$(awk "/$WIFI_IF:/ {print int(\$4)}" /proc/net/wireless 2>/dev/null)
  fi
else
  WIFI_SIGNAL=""
fi

[ -z "$WIFI_SIGNAL" ] && WIFI_SIGNAL=0.0

# Get hostname
HOSTNAME=$(hostname)

# Replace null or empty values with 0.0
[ -z "$CPUTEMP" ] && CPUTEMP=0.0
[ -z "$CPU_LOAD" ] && CPU_LOAD=0.0
[ -z "$DISK_FREE" ] && DISK_FREE=0.0

# Prepare JSON payload
PAYLOAD="{\"cpu_temp\":$CPUTEMP,\"cpu_load\":$CPU_LOAD,\"disk_free_gb\":$DISK_FREE,\"wifi_strength\":$WIFI_SIGNAL,\"hostname\":\"$HOSTNAME\"}"

# Publish to MQTT using mosquitto_pub in a Docker container
docker run --rm eclipse-mosquitto mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_TOPIC" -m "$PAYLOAD" -q 1
if [ $? -ne 0 ]; then
  echo "Failed to publish MQTT message"
  exit 1
fi