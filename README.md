# Plum ecoMAX pellet boiler regulator integration for Home Assistant.
[![ci](https://github.com/denpamusic/homeassistant-plum-ecomax/actions/workflows/ci.yml/badge.svg)](https://github.com/denpamusic/homeassistant-plum-ecomax/actions/workflows/ci.yml)
[![Test Coverage](https://api.codeclimate.com/v1/badges/bfa869d3c97a62eeb71c/test_coverage)](https://codeclimate.com/github/denpamusic/homeassistant-plum-ecomax/test_coverage)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)

## Overview
This Home Assistant integration provides support for ecoMAX controllers manufactured by [Plum Sp. z o.o.](https://www.plum.pl/)

It's based on [PyPlumIO](https://github.com/denpamusic/PyPlumIO) package and supports connection to ecoMAX controller via RS-485 to Ethernet/Wifi converters or via RS-485 to USB adapter.
![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/ecomax.png)

## ecoNET 300
While this integration is built on top of PyPlumIO library, which from the start was intended as ecoNET 300 alternative, **Patryk B** is currently developing awesome HASS integration that communicates with ecoMAX controller via ecoNET 300 device.

If you have an ecoNET 300 device, be sure to [check it out](https://github.com/pblxptr/ecoNET-300-Home-Assistant-Integration)!

## Table of contents
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual](#manual)
- [Configuration](#configuration)
- [Entities](#entities)
  - [Controller](#controller-hub)
  - [Mixers](#mixers-sub-devices)
- [Services](#services)
- [License](#license)

## Installation
### HACS
1. Follow [this guide](https://hacs.xyz/docs/faq/custom_repositories) to add homeassistant-plum-ecomax as custom repository to the HACS.  
URL of the repository:
```
https://github.com/denpamusic/homeassistant-plum-ecomax
```
2. Search for `ecomax` in HACS search window and install `Plum ecoMAX pellet boiler regulator integration`.
3. Restart Home Assistant.

### Manual

1. Clone this repository with:
```sh
git clone https://github.com/denpamusic/homeassistant-plum-ecomax
```

2. Move `custom_components` directory from `homeassistant-plum-ecomax` to your Home Assistant configuration directory. ([next to configuration.yaml](https://www.home-assistant.io/docs/configuration/))

```sh
cp -r ./homeassistant-plum-ecomax/custom_components ~/.homeassistant
```

3. Add empty `plum_ecomax:` section to your `configuration.yaml` file.
4. Restart Home Assistant.


## Configuration

Adding Plum ecoMAX integration to your Home Assistant instance can be done via user interface, by using this My button:


[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=plum_ecomax)
<details>
  <summary><b>Manual Configuration Steps</b></summary>
  
If the above My button doesn’t work, you can also perform the following steps manually:

1. Browse to your Home Assistant instance.
2. In the sidebar click on Settings.
3. From the configuration menu select: Devices & Services.
4. In the bottom right, click on the Add Integration button.
5. From the list, search and select "Plum ecoMAX".

![Search dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/search.png)

6. Enter your connection details and click `Submit`.  
__Serial connection__: you will need to fill Device path. Host and Port will be ignored.  
__TCP connection__: you will need to fill Host and Port. Device path will be ignored

![Configuration dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/config.png)

7. Your device should now be available in your Home Assistant installation.

![Success](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/success.png)
  
</details>

## Entities
This integration provides the following entities, split between controller device and mixer sub-devices.
Not all entities might be available for your controller model. Entities that are deemed as unsupported during
initial setup will be disabled.

> LEGEND: 🇵 - ecoMAX __P-series__ (e. g. ecoMAX 860**p**), 🇮 - ecoMAX __I-series__ (e. g. ecoMAX 850**i**)

### Controller (Hub)
#### Sensors
- Heating temperature
- Water heater temperature
- Outside temperature
- Heating target temperature
- Water heater target temperature 
- Heating mode
- Solar temperature 🇮
- Fireplace temperature 🇮
- Exhaust temperature 🇵
- Feeder temperature 🇵
- Heating load 🇵
- Fan power 🇵
- Fuel level 🇵
- Fuel consumption 🇵
- Total fuel burned 🇵
- Heating power 🇵
- Flame intensity 🇵 _(if supported by the controller)_

#### Binary Sensors
- Heating pump state
- Water heater pump state
- Circulation pump state
- Fireplace pump state 🇮
- Solar pump state 🇮
- Fan state 🇵
- Lighter state 🇵

#### Switches
- Controller power switch
- Water heater disinfection switch
- Water heater pump switch
- Summer mode switch
- Weather control switch 🇵
- Fuzzy logic switch 🇵
- Heating schedule switch 🇵
- Water heater schedule switch 🇵

#### Changeable Numbers
- Heating temperature 🇵
- Minimum heating power 🇵
- Maximum heating power 🇵
- Minimum heating temperature 🇵
- Maximum heating temperature 🇵
- Grate mode temperature 🇵
- Fuel calorific value 🇵 _(in kWh/kg)_

#### Water Heater
The integration provides full control for the connected indirect water heater.  
This includes ability to set target temperature, switch into priority, non-priority mode or turn off.

#### Diagnostics
- Alert
- Service password
- UID
- Software version
- Update capabilities

### Mixers (Sub-Devices)
Mixer are added as sub-device for the controller. Each sub device can contain following entities.

#### Sensors
- Mixer temperature
- Mixer target temperature

#### Binary Sensors
- Mixer pump

#### Numbers
- Mixer temperature
- Minimum mixer temperature
- Maximum mixer temperature
- Day mixer temperature 🇮
- Night mixer temperature 🇮

## Services
This integration provides following services:

### Set parameter
Provides ability to set device/sub-device parameter by name. Any parameter that is supported by the device/sub-device can be used with this service. To get parameter names, please download and open diagnostics data and look for a `parameters` key.

Fields:
- __name__ - parameter name
- __value__ - parameter value (allowed values: positive integer, "on", "off")

Targets (Devices):
- __controller__ (default) - set parameter on the ecoMAX controller itself
- __sub-device__ - set parameter on one of sub-devices (e. g. mixer/circuit)

### Update capabilities
Updates list of sensors and parameters that are supported by the device. This list is then used by integration to determine what entities are supported by the controller. If you're not seeing some entities and/or sub-devices, try pressing this button.

### Calibrate meter 🇵
Allows to set meter to a specific value. Currently this can be used to set a value of a `Total Fuel Burned` sensor.

Targets (Entities):
 - __total_fuel_burned__ - counts total burned fuel in kilograms

Fields:
 - __value__ - target sensor will be set to this value

### Reset meter 🇵
Allows to reset the meter value. Can be used to reset a value for the `Total Fuel Burned` sensor.

Targets (Entities):
 - __total_fuel_burned__ - counts total burned fuel in kilograms

## License
This product is distributed under MIT license.
