"""
InfluxDB Dashboard - Login-free visualization for obsybox sensor data
Provides real-time charts and graphs for weather, safety, and equipment monitoring
"""

from flask import Flask, render_template, jsonify, request
from influxdb import InfluxDBClient
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# InfluxDB Configuration
INFLUX_HOST = '192.168.1.49'
INFLUX_PORT = 8086
INFLUX_DATABASE = 'weather'  # Default database - will be selectable in UI

# Initialize InfluxDB client (without database specified - will switch per query)
client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)


def get_databases():
    """Get list of available databases"""
    try:
        databases = client.get_list_database()
        return [db['name'] for db in databases]
    except Exception as e:
        print(f"Error getting databases: {e}")
        return []


def get_measurements(database=None):
    """Get list of available measurements (tables) in the database"""
    try:
        if database:
            temp_client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=database)
            result = temp_client.query('SHOW MEASUREMENTS')
        else:
            # Use default database if none specified
            temp_client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=INFLUX_DATABASE)
            result = temp_client.query('SHOW MEASUREMENTS')
        
        measurements = []
        if result:
            for point in result.get_points():
                measurements.append(point['name'])
        return measurements
    except Exception as e:
        print(f"Error getting measurements: {e}")
        return []


def query_data(measurement, time_range='1h', field=None, database=None):
    """
    Query data from InfluxDB
    
    Args:
        measurement: Measurement name (e.g., 'weather', 'dewheater')
        time_range: Time range (1h, 6h, 24h, 7d, 30d)
        field: Specific field to query (if None, gets all fields)
        database: Database name (if None, uses default)
    
    Returns:
        List of data points with timestamps and values
    """
    try:
        # Use specified database or default
        db = database or INFLUX_DATABASE
        temp_client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=db)
        
        if field:
            query = f'SELECT "{field}" FROM "{measurement}" WHERE time > now() - {time_range}'
        else:
            query = f'SELECT * FROM "{measurement}" WHERE time > now() - {time_range}'
        
        result = temp_client.query(query)
        points = list(result.get_points())
        return points
    except Exception as e:
        print(f"Error querying data: {e}")
        return []


def get_latest_values(measurement, database=None):
    """Get the most recent values for a measurement"""
    try:
        db = database or INFLUX_DATABASE
        temp_client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=db)
        query = f'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1'
        result = temp_client.query(query)
        points = list(result.get_points())
        return points[0] if points else {}
    except Exception as e:
        print(f"Error getting latest values: {e}")
        return {}


@app.route('/')
def index():
    """Main dashboard page"""
    databases = get_databases()
    measurements = get_measurements()
    return render_template('dashboard.html', 
                         databases=databases,
                         measurements=measurements)


@app.route('/api/databases')
def api_databases():
    """API endpoint to get list of databases"""
    databases = get_databases()
    return jsonify(databases)


@app.route('/api/measurements')
def api_measurements():
    """API endpoint to get list of measurements"""
    database = request.args.get('database', INFLUX_DATABASE)
    measurements = get_measurements(database)
    return jsonify(measurements)


@app.route('/api/data/<path:measurement>')
def api_data(measurement):
    """API endpoint to get data for a specific measurement"""
    time_range = request.args.get('range', '1h')
    field = request.args.get('field', None)
    database = request.args.get('database', INFLUX_DATABASE)
    
    data = query_data(measurement, time_range, field, database)
    return jsonify(data)


@app.route('/api/latest/<path:measurement>')
def api_latest(measurement):
    """API endpoint to get latest values for a measurement"""
    database = request.args.get('database', INFLUX_DATABASE)
    data = get_latest_values(measurement, database)
    return jsonify(data)


@app.route('/api/fields/<path:measurement>')
def api_fields(measurement):
    """API endpoint to get available fields for a measurement"""
    database = request.args.get('database', INFLUX_DATABASE)
    print(f"Getting fields for measurement: '{measurement}' in database: '{database}'")
    try:
        temp_client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT, database=database)
        query = f'SHOW FIELD KEYS FROM "{measurement}"'
        print(f"Executing query: {query}")
        result = temp_client.query(query)
        fields = []
        if result:
            for point in result.get_points():
                fields.append({
                    'name': point['fieldKey'],
                    'type': point['fieldType']
                })
        print(f"Found {len(fields)} fields")
        return jsonify(fields)
    except Exception as e:
        print(f"Error getting fields: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        databases = get_databases()
        return jsonify({
            'status': 'healthy',
            'influx_host': INFLUX_HOST,
            'influx_port': INFLUX_PORT,
            'database': INFLUX_DATABASE,
            'databases_available': len(databases),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


if __name__ == '__main__':
    print(f"Starting InfluxDB Dashboard...")
    print(f"Connecting to InfluxDB at {INFLUX_HOST}:{INFLUX_PORT}")
    print(f"Default database: {INFLUX_DATABASE}")
    print(f"\nAvailable databases: {get_databases()}")
    print(f"Available measurements: {get_measurements()}")
    print(f"\nDashboard will be available at: http://localhost:5000")
    print(f"Also accessible from network at: http://192.168.1.x:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
