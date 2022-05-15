# Plum ecoMAX pellet boiler regulator integration for Home Assistant.
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## Overview
This Home Assistant integration provides support for ecoMAX automatic pellet boilers controllers manufactured by [Plum Sp. z o.o.](https://www.plum.pl/)

It is based on [PyPlumIO](https://github.com/denpamusic/PyPlumIO) package and supports connection to ecoMAX controller via serial network server, for example [Elfin EW11](https://aliexpress.ru/item/4001104348624.html).

This project is currently in __Alpha__ state.

## Table of contents
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual](#manual)
- [Usage](#usage)
- [Tracking spent fuel](#tracking-spent-fuel)
- [Entities](#entities)
- [License](#license)

## Installation
### HACS
1. Follow [this guide](https://hacs.xyz/docs/faq/custom_repositories) to add homeassistant-plum-ecomax as custom repository to the HACS.  
URL of the repository is:
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


## Usage
1. Click `Add Integration` button and search for `Plum ecoMAX`.
2. Enter your connection details and click `Submit`.  
If you select Serial connection type, you need to fill in correct Device path, Host and Port will be ignored.  
Otherwise, if you select TCP connection type, you'll only need to fill Host and Port. Device path can be left as is.   
![Configuration dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/config.png)

3. Your device should now be available in your Home Assistant installation.  
![Success](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/success.png)

## Tracking spent fuel
You can track total burned fuel by utilising built-in [Utility Meter integration](https://www.home-assistant.io/integrations/utility_meter/).

Create new utility meter and specify `Fuel Burned Since Last Update` as it's input sensor.  
Make sure, that `Delta values` setting is enabled.

## Entities
This integration provides following entities.

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
- Fuel Burned Since Last Update
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

### Numbers (Changeable sliders)
- Heating Temperature
- Grate Mode Temperature
- Minimum Heating Power
- Maximum Heating Power
- Minimum Heating Temperature
- Maximum Heating Temperature

### Water Heater
Integration provides full control for connected indirect water heater.  
This includes ability to set target temperature, switch into priority, non-priority mode or turn off.

## License
This product is distributed under MIT license.
