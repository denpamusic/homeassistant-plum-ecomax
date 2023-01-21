# Plum ecoMAX pellet boiler regulator integration for Home Assistant.
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![stability-beta](https://img.shields.io/badge/stability-beta-33bbff.svg)](https://github.com/mkenney/software-guides/blob/master/STABILITY-BADGES.md#beta)

## Overview
This Home Assistant integration provides support for ecoMAX automatic pellet boilers controllers manufactured by [Plum Sp. z o.o.](https://www.plum.pl/)

It's based on [PyPlumIO](https://github.com/denpamusic/PyPlumIO) package and supports connection to ecoMAX controller via RS-485 to Ethernet/Wifi converters or via RS-485 to USB adapter.
![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/ecomax.png)

## Configuration
1. Click `Add Integration` button and search for `Plum ecoMAX`.

![Search dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/search.png)

2. Enter your connection details and click `Submit`.  
__Serial connection__: you will need to fill Device path. Host and Port will be ignored.  
__TCP connection__: you will need to fill Host and Port. Device path will be ignored.

![Configuration dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/config.png)

3. Your device should now be available in your Home Assistant installation.

![Success](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/success.png)

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
