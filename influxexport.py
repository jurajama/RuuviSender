# Script for exporting measurement data from Influxdb to csv-file
# Usage:
# - Install the dependencies: venv/bin/pip install -r requirements.txt
# - Make sure that my_config.py contains your Influxdb connection information.
# - Edit days_to_fetch to define how many days of data shall be fetched.
# - Fetch is done in multiple batches to avoid too heavy individual queries. 

from influxdb import InfluxDBClient
import csv
import os
import datetime
import re
import my_config as conf

FILENAME = "export.csv"

# Set up InfluxDB connection
client = InfluxDBClient(conf.INFLUXDB_HOST, conf.INFLUXDB_PORT, conf.INFLUXDB_USER, conf.INFLUXDB_PWD, conf.INFLUXDB_DATABASE, timeout=600)

# Set batch size and time interval
batch_size_days = 7
delta = datetime.timedelta(days=batch_size_days)

# Set number of days to fetch
days_to_fetch = 365

TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

# Calculate time range for first query (timezone-aware UTC datetimes, seconds precision)
end_time = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
start_time = end_time - datetime.timedelta(days=days_to_fetch)

# Initialize CSV file and write header
with open(FILENAME, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['timestamp', 'sensorId', 'temperature', 'humidity', 'pressure'])

# Loop over date ranges and query InfluxDB for each batch
while end_time > start_time:
    # Calculate time range for current query
    query_end_time = end_time
    query_start_time = max(query_end_time - delta, start_time)

    start_str = query_start_time.strftime(TIME_FORMAT)
    end_str = query_end_time.strftime(TIME_FORMAT)
    print(f"query_start_time: {start_str}   query_end_time: {end_str}")

    # Query data from InfluxDB for current batch
    query = f'SELECT "temperature", "humidity", "pressure", "sensorId" FROM "temps" WHERE time >= \'{start_str}\' AND time <= \'{end_str}\''
    results = client.query(query)

    # Write data to CSV file
    with open(FILENAME, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for point in results.get_points():
            timestamp = point['time']
            sensor_id = point['sensorId']
            temperature = point['temperature']
            humidity = point['humidity']
            pressure = point['pressure']
            if re.match('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', sensor_id):
                writer.writerow([timestamp, sensor_id, temperature, humidity, pressure])

    # Update time range for next query
    end_time = query_start_time

print(f"Data exported to {FILENAME}")
