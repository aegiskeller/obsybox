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
CPU_IDLE=$(top -bn2 -d 0.5 | grep "Cpu(s)" | tail -n1 | awk -F'id,' -v prefix="$prefix" '{split($1, vs, ","); v=vs[length(vs)]; sub("%Cpu(s):", "", v); gsub(" ", "", v); print $4}')
if [ -z "$CPU_IDLE" ]; then
  CPU_IDLE=$(mpstat 1 1 | awk '/Average/ {print $12}')
fi

# Get free disk space on root (in GB)
DISK_FREE=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')

# Get WiFi signal strength (RSSI in dBm)
WIFI_IF=$(iw dev | awk '$1=="Interface"{print $2; exit}')
if [ -n "$WIFI_IF" ]; then
  WIFI_SIGNAL=$(iwconfig "$WIFI_IF" 2>/dev/null | grep -i --color=never 'signal level' | awk -F '=' '{print $3}' | awk '{print $1}')
else
  WIFI_SIGNAL=""
fi

# Prepare JSON payload
PAYLOAD="{\"cpu_temp\":$CPUTEMP,\"cpu_idle\":$CPU_IDLE,\"disk_free_gb\":$DISK_FREE,\"wifi_signal_dbm\":$WIFI_SIGNAL}"

# Publish to MQTT
mosquitto_pub -h "$MQTT_BROKER" -t "$MQTT_TOPIC" -m "$PAYLOAD"