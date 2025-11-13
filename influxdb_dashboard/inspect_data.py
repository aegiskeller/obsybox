"""
InfluxDB Data Inspector - Quick diagnostic tool
Checks InfluxDB connection and shows available data
"""

from influxdb import InfluxDBClient
from datetime import datetime, timedelta
import sys

INFLUX_HOST = '192.168.1.49'
INFLUX_PORT = 8086

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_connection():
    """Test InfluxDB connection"""
    print_section("Testing InfluxDB Connection")
    try:
        client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT)
        client.ping()
        print(f"✅ Successfully connected to InfluxDB at {INFLUX_HOST}:{INFLUX_PORT}")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to InfluxDB: {e}")
        sys.exit(1)

def list_databases(client):
    """List all databases"""
    print_section("Available Databases")
    try:
        databases = client.get_list_database()
        for i, db in enumerate(databases, 1):
            print(f"{i}. {db['name']}")
        return [db['name'] for db in databases]
    except Exception as e:
        print(f"❌ Error listing databases: {e}")
        return []

def inspect_database(client, database):
    """Show measurements and data summary for a database"""
    print_section(f"Inspecting Database: {database}")
    
    try:
        client.switch_database(database)
        
        # Get measurements
        result = client.query('SHOW MEASUREMENTS')
        measurements = [point['name'] for point in result.get_points()]
        
        if not measurements:
            print(f"⚠️  No measurements found in database '{database}'")
            return
        
        print(f"Found {len(measurements)} measurement(s):")
        
        for measurement in measurements:
            print(f"\n📊 Measurement: {measurement}")
            
            # Get field keys
            field_result = client.query(f'SHOW FIELD KEYS FROM "{measurement}"')
            fields = list(field_result.get_points())
            print(f"   Fields: {', '.join([f['fieldKey'] + ' (' + f['fieldType'] + ')' for f in fields])}")
            
            # Get data count
            count_result = client.query(f'SELECT COUNT(*) FROM "{measurement}"')
            count_points = list(count_result.get_points())
            if count_points:
                # Get first field name for count
                first_field = fields[0]['fieldKey'] if fields else None
                if first_field:
                    count = count_points[0].get(f'count_{first_field}', 0)
                    print(f"   Total records: {count}")
            
            # Get time range
            time_result = client.query(f'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1')
            latest_points = list(time_result.get_points())
            
            if latest_points:
                latest = latest_points[0]
                latest_time = datetime.fromisoformat(latest['time'].replace('Z', '+00:00'))
                age = datetime.now(latest_time.tzinfo) - latest_time
                
                print(f"   Latest data: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Data age: {age.days} days, {age.seconds//3600} hours ago")
                
                if age.days > 7:
                    print(f"   ⚠️  WARNING: Data is more than 7 days old!")
                elif age.total_seconds() < 3600:
                    print(f"   ✅ Data is fresh (less than 1 hour old)")
                
                # Show sample values
                print(f"   Latest values:")
                for field in fields[:5]:  # Show up to 5 fields
                    field_name = field['fieldKey']
                    value = latest.get(field_name)
                    if value is not None:
                        if isinstance(value, float):
                            print(f"     - {field_name}: {value:.2f}")
                        else:
                            print(f"     - {field_name}: {value}")
            else:
                print(f"   ⚠️  No data found in this measurement")
    
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")

def check_recent_writes(client, database, hours=1):
    """Check for recent data writes"""
    print_section(f"Recent Writes (Last {hours} hour(s))")
    
    try:
        client.switch_database(database)
        result = client.query('SHOW MEASUREMENTS')
        measurements = [point['name'] for point in result.get_points()]
        
        has_recent_data = False
        
        for measurement in measurements:
            query = f'SELECT * FROM "{measurement}" WHERE time > now() - {hours}h'
            result = client.query(query)
            points = list(result.get_points())
            
            if points:
                has_recent_data = True
                print(f"✅ {measurement}: {len(points)} records in last {hours}h")
            else:
                print(f"⚠️  {measurement}: No data in last {hours}h")
        
        if not has_recent_data:
            print(f"\n⚠️  No recent data found in database '{database}'")
            print(f"   Try checking longer time ranges (6h, 24h, 7d, 30d)")
    
    except Exception as e:
        print(f"❌ Error checking recent writes: {e}")

def main():
    print("\n🔍 InfluxDB Data Inspector for obsybox")
    print(f"Checking InfluxDB at {INFLUX_HOST}:{INFLUX_PORT}")
    
    # Connect
    client = check_connection()
    
    # List databases
    databases = list_databases(client)
    
    if not databases:
        print("❌ No databases found!")
        return
    
    # Inspect each database
    for db in databases:
        if db not in ['_internal']:  # Skip internal database
            inspect_database(client, db)
    
    # Check recent writes for common databases
    common_dbs = ['weather', 'dewheater', 'sensor_data', 'weathersafety']
    for db in common_dbs:
        if db in databases:
            check_recent_writes(client, db, hours=1)
    
    print_section("Summary")
    print("✅ Inspection complete!")
    print("\nNext steps:")
    print("1. If data is old, check that MQTT publishers are running")
    print("2. If no data, verify Node-RED flows are writing to InfluxDB")
    print("3. Use longer time ranges in dashboard (30d) if data is sparse")
    print("4. See TROUBLESHOOTING.md for detailed help")
    print()

if __name__ == '__main__':
    main()
