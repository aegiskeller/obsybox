#!/bin/bash
# Ekos Power-On Script for ObsyBox Switch
# Use this in Ekos Scheduler as a startup script

BASE_URL="http://localhost:8080/api/v1/switch/0"

echo "🔌 Powering on observatory equipment..."

# Turn on Mount (Switch 0)
echo "  ▸ Mount: ON"
curl -s -X PUT "$BASE_URL/setswitch/0" \
  -H "Content-Type: application/json" \
  -d '{"State":true}' > /dev/null

sleep 2

# Turn on Camera (Switch 1)
echo "  ▸ Camera: ON"
curl -s -X PUT "$BASE_URL/setswitch/1" \
  -H "Content-Type: application/json" \
  -d '{"State":true}' > /dev/null

sleep 1

# Turn on Focuser (Switch 2)
echo "  ▸ Focuser: ON"
curl -s -X PUT "$BASE_URL/setswitch/2" \
  -H "Content-Type: application/json" \
  -d '{"State":true}' > /dev/null

echo "✅ Power-on sequence complete"
