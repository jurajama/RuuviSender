# RuuviSender
Sending RuuviTag data scanned by Raspberry to a remote InfluxDB database that is setup with https://github.com/jurajama/TempMonitor.

## Installation

```sudo apt-get install bluez-hcidump
sudo pip install --upgrade pip
sudo pip install setuptools -U
sudo pip install ruuvitag_sensor
sudo pip setup influxdb
```

- Clone repository to /home/pi
- Edit your InfluxDB connection information in my_config.py
- Copy ruuvisender.service to /etc/systemd/system/ruuvisender.service
- sudo systemctl daemon-reload
- sudo systemctl start ruuvisender
- sudo systemctl enable ruuvisender

