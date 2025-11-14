#!/bin/bash
# Ekos Shutdown Script for ObsyBox Switch
# Use this in Ekos Scheduler as a shutdown script

BASE_URL="http://localhost:8080/api/v1/switch/0"

echo "🔌 Powering down observatory equipment..."

# Turn off Camera first (prevent cooler issues)
echo "  ▸ Camera: OFF"
curl -s -X PUT "$BASE_URL/setswitch/1" \
  -H "Content-Type: application/json" \
  -d '{"State":false}' > /dev/null

sleep 1

# Turn off Focuser
echo "  ▸ Focuser: OFF"
curl -s -X PUT "$BASE_URL/setswitch/2" \
  -H "Content-Type: application/json" \
  -d '{"State":false}' > /dev/null

sleep 1

# Turn off Mount last
echo "  ▸ Mount: OFF"
curl -s -X PUT "$BASE_URL/setswitch/0" \
  -H "Content-Type: application/json" \
  -d '{"State":false}' > /dev/null

echo "✅ Shutdown sequence complete"
