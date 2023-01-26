# Plum ecoMAX pellet boiler regulator integration for Home Assistant.
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)

## Overview
This Home Assistant integration provides support for ecoMAX automatic pellet boilers controllers manufactured by [Plum Sp. z o.o.](https://www.plum.pl/)

It's based on [PyPlumIO](https://github.com/denpamusic/PyPlumIO) package and supports connection to ecoMAX controller via RS-485 to Ethernet/Wifi converters or via RS-485 to USB adapter.

![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/ecomax.png)

## Connect the ecoMAX
With this integration you have two ways of connecting to your ecoMAX controller. One is directly connecting the PC that runs Home Assistant via **RS485 to USB adapter**.

Other way is to use **RS485 to WiFi converter**. This has a benefit of being able to move PC that runs Home Assistant away from the boiler and connect to it wirelessly.

![RS485 adapter and converters](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/rs485.png)

Regardless of the chosen method, you'll need to find RS485 port on your ecoMAX controller.
If you have ecoSTER thermostat, it's easy, as ecoSTERs also use RS485 port and you'll just have to connect your adapter/converter in parallel with it.

If you don't have ecoSTER, look for pins that are labeled as "D+" and "D-" then connect your device as follows:
```
Adapter ->  ecoMAX
[A]     ->  [D+]
[B]     ->  [D-]
[GND]   ->  [GND] (optional, less interference)
```

## Configuration
1. Click `Add Integration` button and search for `Plum ecoMAX`.

![Search dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/search.png)

2. Enter your connection details and click `Submit`.  
__Serial connection__: you will need to fill Device path. Host and Port will be ignored.  
__TCP connection__: you will need to fill Host and Port. Device path will be ignored.

![Configuration dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/config.png)

3. Your device should now be available in your Home Assistant installation.

![Success](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/success.png)

## License
This product is distributed under MIT license.
