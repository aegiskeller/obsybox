from influxdb import InfluxDBClient

# Update these values
HOST = 'localhost'   # or the host/IP where the container port is published
PORT = 8086
#USERNAME = 'admin'   # or None if auth disabled
#PASSWORD = 'secret'
DATABASE = 'weather'

def query_points(measurement: str, limit: int = 10):
    client = InfluxDBClient(host=HOST, port=PORT,
                            #username=USERNAME, password=PASSWORD,
                            database=DATABASE, timeout=10)
    q = f'SELECT * FROM "{measurement}" LIMIT {limit}'
    result = client.query(q)
    # result is a ResultSet; iterate points
    for point in result.get_points():
        print(point)

if __name__ == '__main__':
    query_points('weather', limit=10)