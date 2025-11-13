# Dashboard Tabs Feature

## Overview

The Obsybox Dashboard now features a tabbed interface with three main sections for better organization of data visualization.

## Tab Structure

### 1. Environmental Sensors 🌡️
**Database**: `sensor_data`

**Purpose**: Display all environmental monitoring data from observatory sensors

**Features**:
- Shows all measurements from the `sensor_data` database
- Combines data from multiple sensors into unified views
- Auto-categorized stat cards showing latest readings
- Time-series charts for all numeric fields
- Dedicated time range selector
- Auto-refresh option (30 seconds)

**Typical Data**:
- Temperature sensors
- Humidity sensors  
- Dew point measurements
- Sky conditions
- Weather data
- Ambient light levels

### 2. Computing Resources 💻
**Database**: `system_monitoring`

**Purpose**: Monitor system health and performance metrics

**Features**:
- Shows all measurements from the `system_monitoring` database
- Real-time system performance statistics
- Resource usage trends over time
- Dedicated time range selector
- Auto-refresh option (30 seconds)

**Typical Metrics**:
- CPU usage/temperature
- Memory usage (used/available/total)
- Disk usage (used/free/total)
- Network traffic (sent/received)
- System uptime

### 3. Data Exploration 🔍
**Database**: User-selectable

**Purpose**: Flexible data exploration across all databases

**Features**:
- Database selection dropdown
- Measurement selection dropdown (filtered by database)
- Time range selector
- Auto-refresh option (30 seconds)
- Full access to all InfluxDB databases
- Dynamic stat cards and charts based on selection

**Use Cases**:
- Exploring custom databases
- Analyzing specific measurements
- Comparing different time ranges
- Deep-dive into specific data sources

## Usage

### Quick Start

1. **Open the dashboard**: http://localhost:5000 or http://192.168.1.17:5000

2. **Navigate tabs**: Click the tab buttons at the top to switch between sections

3. **Select time range**: Each tab has its own time range selector
   - Last Hour (1h)
   - Last 6 Hours (6h)
   - Last 24 Hours (24h)
   - Last 7 Days (7d)
   - Last 30 Days (30d) - Default

4. **Enable auto-refresh**: Check the "Auto-refresh (30s)" box for live updates

5. **View data**: 
   - **Stat Cards**: Latest values at the top
   - **Charts**: Interactive time-series graphs below
   - **Zoom**: Click and drag on charts
   - **Pan**: Use pan tool in chart toolbar
   - **Download**: Use camera icon to save charts

### Environmental Sensors Tab

**Automatic Loading**: This tab loads automatically when you open the dashboard

**What it shows**: All data from the `sensor_data` database across all measurements

**Best for**: 
- Quick overview of observatory conditions
- Monitoring weather safety
- Checking dew heater status
- Verifying sensor operations

### Computing Resources Tab

**Loading**: Click the "Computing Resources" tab

**What it shows**: All system monitoring data from `system_monitoring` database

**Best for**:
- System performance monitoring
- Resource usage trending
- Identifying performance bottlenecks
- Capacity planning

### Data Exploration Tab

**Loading**: Click the "Data Exploration" tab

**Interactive Controls**:
1. Select a database from the dropdown
2. Select a measurement (auto-populated based on database)
3. Choose time range
4. Click "Refresh Data"

**Best for**:
- Custom database exploration
- Accessing specialized databases (dewheater, weathersafety, etc.)
- Ad-hoc data analysis
- Comparing different data sources

## Technical Details

### Auto-Refresh Behavior

- Each tab has its own auto-refresh checkbox
- Switching tabs clears the auto-refresh timer
- Only one tab can auto-refresh at a time
- 30-second interval for all tabs

### Data Aggregation

**Environmental & Computing Tabs**:
- Query all measurements in the specified database
- Combine stats from all measurements
- Display unified charts with measurement prefixes
- Show latest values from each measurement

**Exploration Tab**:
- Single database/measurement selection
- Traditional single-source visualization
- More focused analysis

### Chart Configuration

All charts feature:
- Plotly.js interactive graphics
- Automatic unit detection
- Date/time x-axis
- Hover tooltips with precise values
- Download as PNG capability
- Responsive resizing

### Supported Units

The dashboard automatically detects and displays units for:

**Environmental**:
- Temperature: °C
- Humidity: %
- Wind speed: m/s
- Light: lux
- Power: W
- Voltage: V
- Current: A

**System Monitoring**:
- CPU/Memory/Disk usage: %
- Temperature: °C
- Memory size: MB
- Disk size: GB
- Network: MB
- Uptime: hours

## Customization

### Adding More Preset Tabs

To add additional preset tabs (like the Environmental and Computing tabs):

1. Add tab button in HTML:
```html
<button class="tab-button" onclick="switchTab('yourtab')">Your Tab Name</button>
```

2. Add tab content section:
```html
<div id="yourtab" class="tab-content">
    <!-- Controls and grid elements -->
</div>
```

3. Add JavaScript load function following the pattern of `loadEnvironmentalData()`

4. Update `switchTab()` to call your load function

### Changing Default Database for Preset Tabs

Edit the `loadEnvironmentalData()` or `loadComputingData()` functions in the template:

```javascript
const database = 'your_database_name';  // Change this line
```

### Styling Tabs

Tab appearance is controlled in the CSS section:
- `.tabs` - Container styling
- `.tab-button` - Individual tab buttons
- `.tab-button.active` - Active tab highlight
- `.tab-content` - Tab content areas

## Troubleshooting

### Tab shows "No measurements found"

**Solutions**:
1. Verify the database name is correct
2. Check if measurements exist: `curl "http://192.168.1.49:8086/query?db=DATABASE_NAME&q=SHOW+MEASUREMENTS"`
3. Ensure data is being written to that database

### Data not loading on tab switch

**Solutions**:
1. Check browser console (F12) for JavaScript errors
2. Verify Flask server is running
3. Check network tab in browser dev tools for failed API calls
4. Ensure InfluxDB is accessible

### Auto-refresh not working

**Solutions**:
1. Uncheck and re-check the auto-refresh box
2. Switch to a different tab and back
3. Check browser console for errors
4. Verify data loads manually with the Refresh button

### Charts not displaying

**Solutions**:
1. Ensure Plotly.js CDN is accessible (check browser console)
2. Verify data is being returned from API (check Network tab)
3. Try a longer time range (30 days)
4. Check if fields are numeric (only numeric fields are charted)

## Performance Considerations

- **Multiple Measurements**: Environmental and Computing tabs query multiple measurements
- **Large Time Ranges**: 30-day queries may take longer with dense data
- **Auto-Refresh**: Can increase server load; use judiciously
- **Concurrent Tabs**: Only active tab loads data; switching pauses inactive tabs

## Future Enhancements

Potential additions:
- Custom tab configuration via settings
- Save/load tab preferences
- Export data from tabs
- Dashboard layouts per tab
- Alert thresholds on stat cards
- Comparison views across measurements
- Historical data analysis tools
