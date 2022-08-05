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
This integration provides the following entities:

### Sensors
- Heating Temperature
- Water Heater Temperature
- Exhaust Temperature
- Outside Temperature
- Heating Target Temperature
- Water Heater Target Temperature
- Feeder Temperature
- Heating Load
- Fan Power
- Fuel Level
- Fuel Consumption
- Total Fuel Burned
- Heating Mode
- Heating Power
- Flame Intensity (if supported by the controller)

### Binary Sensors
- Heating Pump State
- Water Heater Pump State
- Fan State
- Lighter State

### Switches
- Regulator Master Switch
- Weather Control Switch
- Water Heater Disinfection Switch
- Water Heater Pump Switch
- Summer Mode Switch
- Fuzzy Logic Switch

### Changeable Numbers
- Heating Temperature
- Grate Mode Temperature
- Minimum Heating Power
- Maximum Heating Power
- Minimum Heating Temperature
- Maximum Heating Temperature
- Fuel Calorific Value (in kWh/kg)

### Diagnostics
- Service Password
- UID
- Software Version
- Update Capabilities (button)

### Water Heater
Integration provides full control for connected indirect water heater.  
This includes ability to set target temperature, switch into priority, non-priority mode or turn off.

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
