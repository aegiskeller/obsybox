#!/bin/bash

# Settings
MQTT_BROKER="192.168.1.49"
MQTT_TOPIC="obsybox/rpisys"

# Get CPU temperature (in Celsius)
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
  CPUTEMP=$(awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp)
else
  CPUTEMP=$(vcgencmd measure_temp 2>/dev/null | grep -oP '[0-9.]+')
fi

# Get CPU idle percentage (average over 1 second)
CPU_IDLE=$(top -bn2 -d 0.5 | grep "Cpu(s)" | tail -n1 | awk -F'id,' '{split($1, vs, ","); v=vs[length(vs)]; sub("%Cpu(s):", "", v); gsub(" ", "", v); print $4}')
if [ -z "$CPU_IDLE" ]; then
  # Fallback: parse /proc/stat (Linux standard, no extra tools)
  PREV_IDLE=$(awk '/^cpu /{print $5}' /proc/stat)
  PREV_TOTAL=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8+$9+$10}' /proc/stat)
  sleep 1
  IDLE=$(awk '/^cpu /{print $5}' /proc/stat)
  TOTAL=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8+$9+$10}' /proc/stat)
  DIFF_IDLE=$((IDLE - PREV_IDLE))
  DIFF_TOTAL=$((TOTAL - PREV_TOTAL))
  if [ "$DIFF_TOTAL" -gt 0 ]; then
    CPU_IDLE=$(awk "BEGIN { printf \"%.1f\", ($DIFF_IDLE/$DIFF_TOTAL)*100 }")
  else
    CPU_IDLE="0"
  fi
fi

# Get free disk space on root (in GB)
DISK_FREE=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')

# Get WiFi signal strength (RSSI in dBm)
# Try to get the WiFi interface from environment or default to wlan0
WIFI_IF=${WIFI_IFACE:-wlan0}
if ip link show "$WIFI_IF" > /dev/null 2>&1; then
  WIFI_SIGNAL=$(iwconfig "$WIFI_IF" 2>/dev/null | grep -i --color=never 'signal level' | awk -F '=' '{print $3}' | awk '{print $1}')
  # If still empty, try /proc/net/wireless
  if [ -z "$WIFI_SIGNAL" ]; then
    WIFI_SIGNAL=$(awk "/$WIFI_IF:/ {print int(\$4)}" /proc/net/wireless 2>/dev/null)
  fi
else
  WIFI_SIGNAL=""
fi

# If still empty, set to null
if [ -z "$WIFI_SIGNAL" ]; then
  WIFI_SIGNAL=null
fi

# Get hostname
HOSTNAME=$(hostname)

# Replace null or empty values with 0.0
[ -z "$CPUTEMP" ] && CPUTEMP=0.0
[ -z "$CPU_IDLE" ] && CPU_IDLE=0.0
[ -z "$DISK_FREE" ] && DISK_FREE=0.0
[ -z "$WIFI_SIGNAL" ] && WIFI_SIGNAL=0.0

# Prepare JSON payload
PAYLOAD="{\"cpu_temp\":$CPUTEMP,\"cpu_idle\":$CPU_IDLE,\"disk_free_gb\":$DISK_FREE,\"wifi_signal_dbm\":$WIFI_SIGNAL,\"hostname\":\"$HOSTNAME\"}"

# Publish to MQTT using mosquitto_pub in a Docker container
docker run --rm eclipse-mosquitto mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_TOPIC" -m "$PAYLOAD" -q 1
# Check if the command was successful
if [ $? -ne 0 ]; then
  echo "Failed to publish MQTT message"
  exit 1
fi