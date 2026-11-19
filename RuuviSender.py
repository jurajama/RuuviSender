#!/usr/bin/env python3
"""Listen to RuuviTag broadcasts and send the measurements to InfluxDB.

The latest reading of every tag heard during the last SEND_INTERVAL seconds is
written to the "temps" measurement (tag "sensorId" = MAC address). Bluetooth
scanning uses the asynchronous BlueZ/D-Bus based ``bleak`` adapter of the
ruuvitag_sensor package.
"""
import asyncio
import logging
import signal
from datetime import datetime, timezone

from influxdb import InfluxDBClient
from ruuvitag_sensor.ruuvi import RuuviTagSensor

import my_config as conf

SEND_INTERVAL = 60        # seconds between InfluxDB writes
SCAN_RETRY_DELAY = 20     # seconds to wait before restarting a failed BLE scan
FIELDS = ("temperature", "humidity", "pressure")

log = logging.getLogger("RuuviSender")


async def scan(readings: dict) -> None:
    """Collect the latest reading of each tag into ``readings`` (MAC -> data).

    Restarts the scan if it fails, e.g. because Bluetooth was reset.
    """
    while True:
        try:
            async for mac, data in RuuviTagSensor.get_data_async():
                readings[mac] = data
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("BLE scan failed, retrying in %d s", SCAN_RETRY_DELAY)
        else:
            log.error("BLE scan ended unexpectedly, retrying in %d s", SCAN_RETRY_DELAY)
        await asyncio.sleep(SCAN_RETRY_DELAY)


def create_points(readings: dict) -> list:
    """Convert readings to InfluxDB points; values a tag does not report are skipped."""
    timestamp = datetime.now(timezone.utc).isoformat()
    points = []
    for mac, data in readings.items():
        fields = {f: data[f] for f in FIELDS if data.get(f) is not None}
        if fields:
            points.append({
                "measurement": "temps",
                "tags": {"sensorId": mac},
                "time": timestamp,
                "fields": fields,
            })
    return points


def write_points(points: list) -> None:
    """Blocking InfluxDB write (run in a worker thread)."""
    with InfluxDBClient(conf.INFLUXDB_HOST, conf.INFLUXDB_PORT, conf.INFLUXDB_USER,
                        conf.INFLUXDB_PWD, conf.INFLUXDB_DATABASE, timeout=5) as client:
        client.write_points(points)


async def send_periodically(readings: dict) -> None:
    """Every SEND_INTERVAL seconds write the readings received since the last write."""
    while True:
        await asyncio.sleep(SEND_INTERVAL)
        # Hand over the readings and start collecting fresh ones, so a tag that
        # went out of range is not reported with a stale value.
        batch = dict(readings)
        readings.clear()
        points = create_points(batch)
        if not points:
            log.warning("No RuuviTag data received during the last %d s", SEND_INTERVAL)
            continue
        try:
            await asyncio.to_thread(write_points, points)
            log.debug("Sent %d reading(s) to InfluxDB", len(points))
        except Exception:
            log.exception("Writing to InfluxDB failed")


async def main() -> None:
    readings: dict = {}
    tasks = [asyncio.create_task(scan(readings)),
             asyncio.create_task(send_periodically(readings))]

    # Stop cleanly on SIGTERM (systemctl stop) and SIGINT (Ctrl-C).
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: [t.cancel() for t in tasks])

    log.info("RuuviSender starting")
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        log.info("RuuviSender shutting down")


if __name__ == "__main__":
    # stderr goes to the systemd journal when run as a service
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
    asyncio.run(main())
