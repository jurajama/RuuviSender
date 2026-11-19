# RuuviSender
Sending RuuviTag data scanned by Raspberry to a remote InfluxDB database that is setup with https://github.com/jurajama/TempMonitor.

The measurements (temperature, humidity, pressure) are written to the `temps` measurement of an InfluxDB 1.x database,
tagged with the MAC address of the tag as `sensorId`. Bluetooth is scanned with the asynchronous `bleak` adapter of the
[ruuvitag-sensor](https://github.com/ttu/ruuvitag-sensor) package, which talks to BlueZ over D-Bus.

## Requirements

- Raspberry Pi (or other Linux machine) with Bluetooth and BlueZ (`bluetooth` service running)
- Python 3.10 or newer (tested with 3.13)

## Installation

```
sudo apt-get install python3-venv
git clone https://github.com/jurajama/RuuviSender.git /home/pi/RuuviSender
cd /home/pi/RuuviSender
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

- Edit your InfluxDB connection information in `my_config.py` (use a user that has write access to the database)
- Check that `ExecStart` and `WorkingDirectory` in `ruuvisender.service` match your installation path
- `sudo cp ruuvisender.service /etc/systemd/system/ruuvisender.service`
- `sudo systemctl daemon-reload`
- `sudo systemctl enable --now ruuvisender`

The service can run as a normal user as well: add `User=<user>` to the service file, and make sure the user is allowed
to use Bluetooth (D-Bus policy of BlueZ, typically the `bluetooth` group).

Logs: `journalctl -u ruuvisender -f`

## Exporting data

`influxexport.py` exports the stored measurements to a csv file, see the instructions in the file.
