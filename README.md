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

## Table of contents
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual](#manual)
- [Configuration](#configuration)
- [Entities](#entities)
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
This integration provides the following entities:

### Sensors
- Heating Temperature
- Water Heater Temperature
- Outside Temperature
- Heating Target Temperature
- Water Heater Target Temperature
- Heating Mode
- Solar Temperature (I-series)
- Fireplace Temperature (I-series)
- Exhaust Temperature (P-series)
- Feeder Temperature (P-series)
- Heating Load (P-series)
- Fan Power (P-series)
- Fuel Level (P-series)
- Fuel Consumption (P-series)
- Total Fuel Burned (P-series)
- Heating Power (P-series)
- Flame Intensity (P-series, if supported by the controller) 

### Binary Sensors
- Heating Pump State
- Water Heater Pump State
- Circulation Pump State
- Fireplace Pump State (I-series)
- Solar Pump State (I-series)
- Fan State (P-series)
- Lighter State (P-series)

### Switches
- Regulator Master Switch
- Water Heater Disinfection Switch
- Water Heater Pump Switch
- Summer Mode Switch
- Weather Control Switch (P-series)
- Fuzzy Logic Switch (P-series)
- Heating Schedule Switch (P-series)
- Water Heater Schedule Switch (P-series)

### Changeable Numbers
- Heating Temperature (P-series)
- Minimum Heating Power (P-series)
- Maximum Heating Power (P-series)
- Minimum Heating Temperature (P-series)
- Maximum Heating Temperature (P-series)
- Grate Mode Temperature (P-series)
- Fuel Calorific Value (P-series, in kWh/kg)

### Diagnostics
- Service Password
- UID
- Software Version
- Update Capabilities

### Water Heater
Integration provides full control for connected indirect water heater.  
This includes ability to set target temperature, switch into priority, non-priority mode or turn off.

### Mixers
Integration provides ability to set and view temperature and pump status of connected mixers.

## Services
This integration provides the following services:

### Set Parameter
Provides ability to set device parameter by name. Any parameter that is supported by the device can be used with this service. To get parameter names, please download and open diagnostics data and look for a `parameters` key.

Fields:
- __name__ - parameter name
- __value__ - parameter value (allowed values: positive integer, "on", "off")

### Update Capabilities
Updates list of sensors and parameters that are supported by the device. Can be useful if new features has been introduced by the firmware update.

### Calibrate Meter
Allows to set meter to the specific value. Can be used to set a value for total fuel burned sensor.

Targets:
 - __total_fuel_burned__ - counts total burned fuel in kilograms

Fields:
 - __value__ - target sensor will be set to this value

### Reset Meter
Allows to reset the meter value. Can be used to reset a value for the total fuel burned sensor.

Targets:
 - __total_fuel_burned__ - counts total burned fuel in kilograms

## License
This product is distributed under MIT license.
