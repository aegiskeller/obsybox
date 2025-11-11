# Configuration file for InfluxDB Dashboard
# Edit these values to match your setup

# InfluxDB Connection
INFLUX_HOST = '192.168.1.49'
INFLUX_PORT = 8086
INFLUX_DATABASE = 'obsybox'

# Optional: InfluxDB Authentication (if enabled)
# INFLUX_USERNAME = 'your_username'
# INFLUX_PASSWORD = 'your_password'

# Dashboard Settings
DASHBOARD_PORT = 5000
DASHBOARD_HOST = '0.0.0.0'  # 0.0.0.0 allows network access
DEBUG_MODE = True  # Set to False for production

# Auto-refresh interval (seconds) - can be changed in UI
AUTO_REFRESH_INTERVAL = 30

# Default time range for charts
DEFAULT_TIME_RANGE = '6h'

# Chart configuration
CHART_HEIGHT = 300  # pixels
CHART_THEME = 'plotly'  # or 'plotly_dark', 'plotly_white'
