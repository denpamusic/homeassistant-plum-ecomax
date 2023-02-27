# Plum ecoMAX pellet boiler regulator integration for Home Assistant.
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)

## Overview
This Home Assistant integration provides support for ecoMAX boilers controllers manufactured by [Plum Sp. z o.o.](https://www.plum.pl/)

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

2. Select you connection type. Choose serial port if your ecoMAX controller is connected directly to the PC that is running Home Assistant, choose network if ecoMAX is connected via RS-485 to WiFi converter

![Menu](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/menu.png)__

To connect via the network fill Host and Port:

![TCP](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/tcp.png)

To connect via serial port fill the Device path:

![serial](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/serial.png)

3. Your device should now be available in your Home Assistant installation.

![Success](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/success.png)

## License
This product is distributed under MIT license.
