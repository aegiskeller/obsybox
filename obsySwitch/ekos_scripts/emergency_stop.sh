#!/bin/bash
# Emergency Stop - Turn off ALL switches immediately
# Use this in Ekos abort procedures

BASE_URL="http://localhost:8080/api/v1/switch/0"

echo "🚨 EMERGENCY STOP - Killing all power..."

# Use emergency stop API endpoint
curl -s -X PUT "$BASE_URL/action" \
  -H "Content-Type: application/json" \
  -d '{"Action":"Emergency_Stop","Parameters":""}' > /dev/null

echo "🛑 All equipment powered OFF"
