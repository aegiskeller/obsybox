# Troubleshooting Guide - No Data Issues

## Quick Diagnostics

If the dashboard shows "No data available", follow these steps:

### 1. Check InfluxDB Connection

Open PowerShell and test the connection:

```powershell
curl http://192.168.1.49:8086/ping
```

Should return: `204 No Content` (this is good!)

### 2. List Available Databases

```powershell
curl "http://192.168.1.49:8086/query?q=SHOW+DATABASES"
```

You should see databases like: `weather`, `dewheater`, `sensor_data`, etc.

### 3. Check Measurements in a Database

```powershell
curl "http://192.168.1.49:8086/query?db=weather&q=SHOW+MEASUREMENTS"
```

Replace `weather` with your database name.

### 4. Check if Data Exists

```powershell
# Get last 5 records from weather database
curl "http://192.168.1.49:8086/query?db=weather&q=SELECT+*+FROM+weather+ORDER+BY+time+DESC+LIMIT+5"
```

### 5. Check Data Age

If you see data but it's old (like from June 2025), the issue is that:
- Data is not currently being written
- You need to select a longer time range in the dashboard

**Solution**: In the dashboard, change the time range dropdown to "Last 30 Days" or "Last 7 Days"

### 6. Common Issues

#### Issue: "No data available for selected time range"

**Solutions**:
1. Select a longer time range (30 days instead of 1 hour)
2. Check if MQTT topics are publishing data
3. Verify Node-RED flows are writing to InfluxDB
4. Check that the correct database is selected

#### Issue: Dashboard shows but no measurements appear

**Solutions**:
1. Select the correct database from the dropdown
2. Verify measurements exist using the curl command above
3. Check InfluxDB logs: `docker logs influxdb`

#### Issue: Charts appear but values are all zero/null

**Solutions**:
1. Check field types - only numeric fields are charted
2. Verify data has non-null values
3. Check for recent data writes

### 7. Testing Data Flow

To verify your MQTT → InfluxDB pipeline is working:

1. **Check MQTT messages**:
```powershell
# Install mosquitto clients first
mosquitto_sub -h 192.168.1.49 -t "obsybox/#" -v
```

2. **Manually write test data** (if needed):
```powershell
$body = @"
{
    "database": "weather",
    "measurement": "test",
    "tags": {},
    "fields": {"value": 42.0},
    "timestamp": $(Get-Date -UFormat %s)000000000
}
"@

curl -X POST "http://192.168.1.49:8086/write?db=weather" -d "test value=42.0"
```

3. **Query it back**:
```powershell
curl "http://192.168.1.49:8086/query?db=weather&q=SELECT+*+FROM+test"
```

### 8. Verify Node-RED InfluxDB Integration

If you're using Node-RED to write MQTT data to InfluxDB:

1. Open Node-RED: http://192.168.1.49:1880
2. Check InfluxDB output nodes are configured correctly
3. Look for error messages in Node-RED debug panel
4. Verify InfluxDB node settings:
   - Host: 192.168.1.49 or influxdb (if using Docker network)
   - Port: 8086
   - Database: correct database name
   - Measurement: correct measurement name

### 9. Dashboard-Specific Checks

In the browser console (F12), check for errors:

- Network errors → InfluxDB connection issue
- CORS errors → Add Flask-CORS if accessing from different network
- API errors → Check Flask server logs

### 10. Still Not Working?

1. **Restart InfluxDB**:
```powershell
docker restart influxdb
```

2. **Check InfluxDB logs**:
```powershell
docker logs influxdb --tail 50
```

3. **Verify Docker network**:
```powershell
docker network inspect iotstack_default
```

4. **Test direct InfluxDB query from Python**:
```python
from influxdb import InfluxDBClient
client = InfluxDBClient(host='192.168.1.49', port=8086)
print(client.get_list_database())
client.switch_database('weather')
result = client.query('SELECT * FROM weather LIMIT 5')
print(list(result.get_points()))
```

## Data Is Old (Not Current)

If you see data but it's from weeks/months ago:

### Check What's Writing Data

1. **MQTT Publishers**: Verify Arduino devices are sending data
   - Check device web interfaces (e.g., http://192.168.1.74 for dew heater)
   - Verify MQTT broker is receiving messages

2. **Windows Task Scheduler**: Check `getweather_mqtt` task is running
   - Task Scheduler → Task Scheduler Library
   - Right-click → Run to test

3. **Node-RED**: Ensure flows are deployed and running
   - http://192.168.1.49:1880
   - Click Deploy button if flows were modified

### Enable Continuous Data Writes

Make sure all your data sources are actively writing:
- Arduino devices powered on and connected
- MQTT broker running
- Node-RED flows deployed
- Windows scheduled tasks active

## Success Indicators

When everything is working, you should see:

✅ Database dropdown populated with multiple databases  
✅ Measurement dropdown shows measurements when database selected  
✅ Stat cards show current values  
✅ Charts display with data points  
✅ Status shows "Last updated: [current time] | X data points"  
✅ Auto-refresh updates charts every 30 seconds  

## Getting Help

If still stuck, gather this info:
1. Screenshot of dashboard showing error
2. Browser console errors (F12)
3. Flask server output (terminal window)
4. Output of curl commands above
5. InfluxDB database and measurement names you're trying to access
