# Ebus heating interface

Having just had a new boiler installed which uses Ebus to communicate round the house, I was interested to be able to read the Ebus messages and check the status of the various parts of the heating system.

So time to press into service a Raspberry Pi using the [ebusd](https://github.com/john30/ebusd) software by John30.

*Source: <https://congoblue.me/ebus.htm>*

## Setup

### Static IP

Set the Pi to a static IP:

```sh
sudo nano /etc/dhcpcd.conf
```

Uncomment the static IP section at the bottom (`interface eth0`, `static ip_address=192.168.1.XX/24` etc).

### Hardware interface

A little bit of electronics is needed to interface to the ebus. I made the ebus interface from here:
<https://ebus.github.io/adapter/index.en.html>

### Install ebusd

- Install ebusd: <https://github.com/john30/ebusd/wiki/1.-Build-and-install>
- Configure ebusd to run on boot: <https://github.com/john30/ebusd/wiki/2.-Run>

Make the folder `/var/ebusd/html` (sudo), then copy the static html into the ebus html folder just created:

```sh
sudo mkdir -p /var/ebusd/html
cd /var/ebusd/html
sudo cp -a /home/pi/ebusd/contrib/html/. .
```

### UART driver

Enable the RPi UART to be used for ebus (special driver — normally it has a 2 char FIFO):
<https://github.com/eBUS/ttyebus>

### ebusd options

```sh
sudo nano /etc/default/ebusd
```

Set options — enable auto scan, set device to internal uart, allow for latency, enable http interface:

```sh
EBUSD_OPTS="--scanconfig -device=/dev/ttyebus --latency=20000 --httpport=8080 --mqtt port=1883 --mqttjson"
```

## Using ebusd

To see what ebusd is doing:

```sh
ebusctl state
ebusctl info
ebusctl find          # shows list of all possible parameters found on the ebus
ebusctl read [name]   # shows value for parameter name, as found in the "find" list above
```

To run ebusd on the command line, stop the service first:

```sh
sudo service ebusd stop
```

Then test the uart link for stuff being received:

```sh
ebusd -f -c /tmp --logareas bus --loglevel info --lograwdata=bytes -d /dev/ttyebus
```

Or trigger a full scan:

```sh
ebusd --scanconfig=full -d /dev/ttyebus
```

- To see http: `http://[ipaddr]:8080`
- To see latest data: `http://[ipaddr]:8080/data`
- To see the ebus logfile: `nano /var/log/ebusd.log`

## MQTT

Install the mosquitto broker for mqtt connections (allows dashboardy thing):

```sh
sudo apt install -y mosquitto mosquitto-clients
```

Set to auto run:

```sh
sudo systemctl enable mosquitto.service
```

It does not seem to update as often as the ebus data does. Not sure why.

## VRT350 room controller

The VRT350 room controller does not work with the automatic config files for ebusd. But it does work with the 370 config file.

1. Download all the config files into `/home/pi/config`.
2. Update the ebusd config file to add the option `--configpath=/home/pi/config/ebusd-configuration/latest/en`.
3. Edit `15.350.csv` to replace everything but the top 2 lines with the lines from `15.370.csv`.

By changing the `r` at the beginning to `r9` you can make ebusd poll for the latest values (ie ask on the ebus for it). Not sure I want to do this, would be better to request via http.

You can request an update using:

```sh
ebusctl read DisplayedRoomTemp -f
```

However this does not always seem to update. You should also be able to do it via http:

```
http://[ipaddr]:8080/data/350/displayedroomtemp?exact=true&maxage=0
```

But this seems to send a read command once, then it won't send the read again for quite a long time (not sure how long).

Eventually I have got round this by implementing TCP in the python script, and sending a read command by tcp with the `-f` option. This forces a read and does work.

## Graphing

I'd really like to be able to see graphs of how the values change over the day.

To do this I will write a python program which logs all the values to a csv file. Each day will have its own csv. The python will log every 10s but only if the data has changed.

Then we'll have a bit of javascript using canvas.js to render a graph out of the csv file.

There seem to be 2 problems here — one is getting the roomtemp to update as described above. The other is keeping the python running; any slight problem and it will crash out. I have put lots of `try...` blocks in to try to catch all the potential problems.

### Running the logger

To run the python from the command line and keep it running use:

```sh
setsid python3 disptest.py < /dev/zero >& /dev/null &
```

(The `&` at the end makes it run in the background. The redirects are to prevent keyboard input and discard the output.)

> **Note:** an earlier version redirected output to `ebuslog.log`
> (`setsid python3 disptest.py < /dev/zero >& ebuslog.log &`). This makes an enormous logfile which eventually crashes the Pi, so redirect to `/dev/null` instead.

To check if it's still running use:

```sh
ps -ef
```

To make it run on boot, put this line in `/etc/rc.local`.

Eventually I have it working, and it is very good.

## Screenshots

The mqtt feed:

<img src="http://www.congoblue.me/Screenshot_20191026-121639_Chrome.jpg" alt="MQTT feed" width="338">

The graphs:

![ebusd](https://congoblue.me/ebusd.png)

[![Heating graph](http://www.congoblue.me/heatgraph.png)](https://congoblue.me/ebus.png)

From the top:

| Colour | Trace |
|---|---|
| Green | Flow target temp from thermostat |
| Blue | Boiler flow |
| Red | Boiler return |
| Cyan | Hot water temp |
| Light blue | Valve state (up = heating, down = hot water, centre = off) |
| Orange | Actual room temp |
| Purple | Boiler run (higher line is hot water mode) |
