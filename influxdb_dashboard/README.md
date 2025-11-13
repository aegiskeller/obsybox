# InfluxDB Dashboard

A lightweight, login-free web dashboard for visualizing obsybox sensor data stored in InfluxDB. Alternative to Grafana without authentication requirements.


## Quick Start

### 1. Install Dependencies

```powershell
# Navigate to the dashboard directory
cd c:\Users\Admin\Documents\Arduino\obsybox\influxdb_dashboard

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Configure Database (if needed)

Edit `app.py` if your InfluxDB setup differs:

```python
INFLUX_HOST = '192.168.1.49'  # Your InfluxDB host
INFLUX_PORT = 8086
INFLUX_DATABASE = 'obsybox'   # Default database name
```

### 3. Run the Dashboard

```powershell
# Using Python directly
python app.py

# Or double-click the launcher
run_dashboard.bat
```

The dashboard will start at:
- Local: http://localhost:5000
- Network: http://192.168.1.x:5000 (where x is your PC's IP)

## Usage

### Dashboard Controls

1. **Database** - Select which InfluxDB database to query
2. **Measurement** - Choose the measurement/table (e.g., weather, dewheater)
3. **Time Range** - Select how far back to display data:
   - Last Hour (1h)
   - Last 6 Hours (6h) - default
   - Last 24 Hours (24h)
   - Last 7 Days (7d)
   - Last 30 Days (30d)
4. **Refresh Data** - Manually reload the dashboard
5. **Auto-refresh** - Enable automatic updates every 30 seconds

### Dashboard Sections

**Stat Cards** - Top section shows latest values for all numeric fields

**Time-Series Charts** - Interactive graphs for each field:
- Zoom: Click and drag on chart
- Pan: Click the pan tool in chart toolbar
- Reset: Double-click chart
- Download: Use camera icon to save chart as PNG

## API Endpoints

The dashboard exposes several API endpoints for programmatic access:

- `GET /` - Main dashboard page
- `GET /health` - Health check and connection status
- `GET /api/databases` - List all databases
- `GET /api/measurements?database=<db>` - List measurements in database
- `GET /api/data/<measurement>?range=<time>` - Get time-series data
- `GET /api/latest/<measurement>` - Get most recent values
- `GET /api/fields/<measurement>` - Get field names and types

Example API usage:
```bash
# Get latest weather data
curl http://localhost:5000/api/latest/weather

# Get dew heater data for last 24 hours
curl http://localhost:5000/api/data/dewheater?range=24h
```

## Customization

### Adding Custom Units

Edit the `getUnit()` function in `templates/dashboard.html`:

```javascript
function getUnit(fieldName) {
    const units = {
        'ambtemp': '°C',
        'your_field': 'your_unit',
        // Add more mappings here
    };
    return units[fieldName.toLowerCase()] || '';
}
```

### Changing Auto-Refresh Interval

In `templates/dashboard.html`, modify the interval (in milliseconds):

```javascript
autoRefreshInterval = setInterval(loadData, 30000); // 30 seconds
```

### Styling

All CSS is contained in `templates/dashboard.html` in the `<style>` section. Modify colors, fonts, and layouts as needed.

## Troubleshooting

### Cannot Connect to InfluxDB

1. Verify InfluxDB is running:
   ```powershell
   curl http://192.168.1.49:8086/ping
   ```

2. Check if database exists:
   ```powershell
   curl http://192.168.1.49:8086/query?q=SHOW+DATABASES
   ```

3. Ensure firewall allows port 8086

### No Data Showing

1. Check if measurements exist:
   - Visit the dashboard
   - Select your database
   - Check if measurements appear in dropdown

2. Verify data is being written:
   - Use InfluxDB CLI or Grafana to confirm data exists
   - Check time range - try "Last 30 Days" to ensure you're not querying empty range

### Port 5000 Already in Use

Change the port in `app.py`:

```python
app.run(host='0.0.0.0', port=5001, debug=True)  # Use 5001 instead
```

## Integration with obsybox

The dashboard automatically detects and visualizes data from:

- **Weather Sensors** - Temperature, humidity, wind speed
- **Dew Heater** - Ambient temp, telescope temp, dew point, heater power
- **Safety Monitor** - Weather safety status
- **Sky Sensors** - Lux, sky temperature, ambient light
- **Power Monitoring** - Tapo P110 power usage
- **Anemometer** - Wind speed data

All MQTT topics that publish to InfluxDB will be available for visualization.

## Production Deployment

For production use (always running):

1. **Windows Service** - Use NSSM to run as a service
2. **Task Scheduler** - Create a task to start on boot
3. **Different WSGI Server** - Replace Flask dev server with Waitress:

```powershell
pip install waitress
```

Create `production.py`:
```python
from waitress import serve
from app import app

serve(app, host='0.0.0.0', port=5000)
```

## Security Notes

⚠️ **This dashboard has NO authentication** - It's designed for local network use only.

For internet exposure, consider:
- Running behind a reverse proxy with authentication
- Using VPN to access your network
- Adding HTTP basic auth with Flask extensions
- Firewall rules to restrict access

## License

Part of the obsybox project. See LICENSE file in repository root.

## Contributing

Found a bug or have a feature request? Open an issue in the obsybox repository.
