#!/bin/bash
# Check status of all switches
# Use for troubleshooting or pre-flight checks

BASE_URL="http://localhost:8080/api/v1/switch/0"

echo "📊 ObsyBox Switch Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if server is running
if ! curl -s --connect-timeout 2 "$BASE_URL/../../../status" > /dev/null 2>&1; then
    echo "❌ ERROR: Alpaca server not running!"
    echo "   Start with: python ascom_switch_server.py"
    exit 1
fi

echo "✅ Alpaca server: ONLINE"
echo ""

# Get status for each switch
for i in {0..3}; do
    name=$(curl -s "$BASE_URL/getswitchname/$i" | grep -o '"Value":"[^"]*"' | cut -d'"' -f4)
    state=$(curl -s "$BASE_URL/getswitch/$i" | grep -o '"Value":[^,}]*' | cut -d':' -f2)
    
    if [ "$state" = "true" ]; then
        echo "🟢 Switch $i ($name): ON"
    else
        echo "⚫ Switch $i ($name): OFF"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
