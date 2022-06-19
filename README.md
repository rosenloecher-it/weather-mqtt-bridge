# weather-mqtt-bridge (Froggit WH2600)

Collects provided information of a Froggit WH2600 SE weather station (local website) and push's it to 
[MQTT](https://en.wikipedia.org/wiki/MQTT).

Supported are only the older "WH2600 SE" weather stations without a "PRO WIFI" suffix. These devices provide the data as HTML 
(via embedded webserver). Tested only with firmware version 2.2.8 and 4.6.2. Other firmware versions may produce different HTML. 

[MQTT](https://en.wikipedia.org/wiki/MQTT) is widely supported by the most smarthome systems.

Features:
- Command line utils or runs as Linux service.
- Send s JSON message, sample:
    ```json
    {"battery-inside": "Normal", "battery-outside": "Normal", "humi-inside": 48.0, "humi-outside": 94.0, "pressure-abs": 980.3, "pressure-rel": 1011.8, "rain-counter": 0.3, "rain-hourly": 0.0, "solar-radiation": 64.01, "status": "success", "temp-inside": 22.1, "temp-outside": 1.2, "timestamp": "2022-01-08T10:56:00", "uv": 251.0, "uvi": 1.0, "wind-direction": 223.0, "wind-gust": 0.0, "wind-speed": 0.0}
    ```
- Calculates relative barometric pressure (strange results with the provided calculation)
- An additional MQTT channel for service status may be configured, which shows if the service is running or not.
  There were issues, that the weather station did not respond after some time and had to be restarted.
  With that service channel a smarthome socket could be controlled. But a digital timer switch socket could be the trick too.

## Startup

### Prepare python environment
```bash
cd /opt
sudo mkdir weather-mqtt-bridge
sudo chown <user>:<user> weather-mqtt-bridge  # type in your user
git clone https://github.com/rosenloecher-it/weather-mqtt-bridge weather-mqtt-bridge

cd weather-mqtt-bridge
virtualenv -p /usr/bin/python3 venv

# activate venv
source ./venv/bin/activate

# check python version >= 3.7
python --version

# install required packages
pip install -r requirements.txt
```

### Configuration

```bash
# cd ... goto project dir
cp ./weather-mqtt-bridge.yaml.sample ./weather-mqtt-bridge.yaml

# security concerns: make sure, no one can read the stored passwords
chmod 600 ./weather-mqtt-bridge.yaml
```

Edit your `weather-mqtt-bridge.yaml`. See comments there.

### Run

```bash
# see command line options
./weather-mqtt-bridge.sh --help

# prepare your own config file based on ./weather-mqtt-bridge.yaml.sample
# the embedded json schema may contain additional information
./weather-mqtt-bridge.sh --json-schema

# start the logger
./weather-mqtt-bridge.sh --print-logs --config-file ./weather-mqtt-bridge.yaml
# abort with ctrl+c

```

## Register as systemd service
```bash
# prepare your own service script based on weather-mqtt-bridge.service.sample
cp ./weather-mqtt-bridge.service.sample ./weather-mqtt-bridge.service

# edit/adapt paths and user in weather-mqtt-bridge.service
vi ./weather-mqtt-bridge.service

# install service
sudo cp ./weather-mqtt-bridge.service /etc/systemd/system/
# alternativ: sudo cp ./weather-mqtt-bridge.service.sample /etc/systemd/system//weather-mqtt-bridge.service
# after changes
sudo systemctl daemon-reload

# start service
sudo systemctl start weather-mqtt-bridge

# check logs
journalctl -u weather-mqtt-bridge
journalctl -u weather-mqtt-bridge --no-pager --since "5 minutes ago"

# enable autostart at boot time
sudo systemctl enable weather-mqtt-bridge.service
```

## Additional infos

### MQTT broker related infos

If no messages get logged check your broker.
```bash
sudo apt-get install mosquitto-clients

# prepare credentials
SERVER="<your server>"

# start listener
mosquitto_sub -h $SERVER -d -t smarthome/#

# send single message
mosquitto_pub -h $SERVER -d -t smarthome/test -m "test_$(date)"

# just as info: clear retained messages
mosquitto_pub -h $SERVER -d -t smarthome/test -n -r -d
```

## Maintainer & License

MIT © [Raul Rosenlöcher](https://github.com/rosenloecher-it)

The code is available at [GitHub][home].

[home]: https://github.com/rosenloecher-it/weather-mqtt-bridge
