#! /usr/bin/python
# -*- coding: utf-8 -*-
import os, sys, datetime, io, time,traceback, requests, logging, threading

from logging.handlers import RotatingFileHandler
from influxdb import InfluxDBClient
from ruuvitag_sensor.ruuvi import RuuviTagSensor

import my_config as conf

# This application listens to RuuviTag broadcasts and sends data to InfluxDB database.

G_SEND_INTERVAL = 60

log = None

g_callback = None

def scanthread():
    RuuviTagSensor.get_datas(g_callback)

class RuuviSender():
    def __init__(self, run_as_service = False):
        self.run_as_service = run_as_service
        self._running = False

        self.datastore = {}

        if run_as_service:
            self.write_pid_file()

    def start(self):
        global g_callback
        g_callback = self.handle_data

        self._running = True

        thread1 = threading.Thread(target = scanthread, args = ())
        thread1.daemon = True
        thread1.start()

        while(self._running):
            time.sleep(G_SEND_INTERVAL)
            self.send_data()

    def handle_data(self, found_data):
#        print('MAC ' + found_data[0])
#        print(found_data[1])
        # key is mac-address, value is measurement data dictionary
        self.datastore[found_data[0]] = found_data[1]

    def write_pid_file(self):
        pid = str(os.getpid())
        f = open('/var/run/ruuvisender.pid', 'w')
        f.write(pid)
        f.close()

    def create_influx_json(self, mac, data):
        timestamp = datetime.datetime.utcnow()
        str_timestamp = timestamp.isoformat("T") + "Z"

        json_temp = [
            {
                "measurement": "temps",
                "tags": {
                    "sensorId": mac
                },
                "time": str_timestamp,
                "fields": {
                   "temperature": data["temperature"],
                   "humidity": data["humidity"],
                   "pressure": data["pressure"]
                }
            }
        ]
#        print("returning json with timestamp " + str_timestamp)
        return json_temp

    def send_data(self):
#        print("in send_data")
        for mac in self.datastore:
            json = self.create_influx_json(mac, self.datastore[mac])

            client = InfluxDBClient(conf.INFLUXDB_HOST, conf.INFLUXDB_PORT, conf.INFLUXDB_USER, conf.INFLUXDB_PWD, conf.INFLUXDB_DATABASE, timeout=5)
            client.write_points(json)

###########################################
# Main function
###########################################

if __name__ == '__main__':

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.error("RuuviSender starting")

    sender = RuuviSender(run_as_service = True)

    try:
        sender.start()
    except KeyboardInterrupt:
        logger.error("Shutting down after KeyboardInterrupt")
    except:
        logger.error("Exception in router_monitor")
        logger.error(traceback.format_exc())
        raise

