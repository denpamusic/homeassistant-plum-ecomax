# Plum ecoMAX boiler controller integration for Home Assistant.
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
- [Connect the ecoMAX](#connect-the-ecomax)
- [Configuration](#configuration)
- [Entities](#entities)
  - [Controller](#controller-hub)
  - [Water Heater](#water-heater)
  - [Thermostats](#thermostats)
  - [Mixers/Circuits](#mixerscircuits-sub-devices)
- [Services](#services)
- [License](#license)

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

### ecoNET 300
While this integration is built on top of PyPlumIO library, which from the start was intended as ecoNET 300 alternative, **Patryk B** is currently developing awesome HASS integration that communicates with ecoMAX controller via ecoNET 300 device.

If you have an ecoNET 300 device, be sure to [check it out](https://github.com/pblxptr/ecoNET-300-Home-Assistant-Integration)!

## Installation
### HACS
1. Follow [this guide](https://hacs.xyz/docs/faq/custom_repositories) to add homeassistant-plum-ecomax as custom repository to the HACS.  
URL of the repository:
```
https://github.com/denpamusic/homeassistant-plum-ecomax
```
2. Search for `ecomax` in HACS search window and install `Plum ecoMAX boiler controller integration`.
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
This integration provides the following entities, split between controller device and sub-devices.

Not all entities might be available for your controller model and entities that are deemed as unsupported during
initial setup will be disabled.

ecoMAX pellet boiler controller model names has a "**p**" suffix (e. g. ecoMAX 850p), ecoMAX installation controller model names have an "**i**" suffix (e. g. ecoMAX 850i).

### Controller (Hub)
Following section lists entities that are added to the ecoMAX device.

#### Sensors
Sensors can have numerical or text state.
Temperature changes that are less than 0.1°C are ignored. 

| Name                                   | Unit | ecoMAX pellet      | ecoMAX installation |
|----------------------------------------|:----:|:------------------:|:-------------------:|
| Heating temperature                    | °C   | :white_check_mark: | :white_check_mark:  |
| Water heater temperature               | °C   | :white_check_mark: | :white_check_mark:  |
| Outside temperature                    | °C   | :white_check_mark: | :white_check_mark:  |
| Heating target temperature             | °C   | :white_check_mark: | :white_check_mark:  |
| Water heater target temperature        | °C   | :white_check_mark: | :white_check_mark:  |
| Heating mode                           | n/a  | :white_check_mark: | :white_check_mark:  |
| Solar temperature                      | °C   | :x:                | :white_check_mark:  |
| Fireplace temperature                  | °C   | :x:                | :white_check_mark:  |
| Exhaust temperature                    | °C   | :white_check_mark: | :x:                 |
| Feeder temperature                     | °C   | :white_check_mark: | :x:                 |
| Return temperature                     | °C   | :white_check_mark: | :x:                 |
| Heating load                           | %    | :white_check_mark: | :x:                 |
| Fan power                              | %    | :white_check_mark: | :x:                 |
| Fuel level                             | %    | :white_check_mark: | :x:                 |
| Fuel consumption                       | kg   | :white_check_mark: | :x:                 |
| Total fuel burned <sup>1</sup>         | kg   | :white_check_mark: | :x:                 |
| Heating power                          | kW   | :white_check_mark: | :x:                 |
| Lower buffer temperature <sup>2</sup>  | °C   | :white_check_mark: | :x:                 |
| Upper buffer temperature <sup>2</sup>  | °C   | :white_check_mark: | :x:                 |
| Flame intensity <sup>2</sup>           | %    | :white_check_mark: | :x:                 |
| Oxygen level <sup>3</sup>              | %    | :white_check_mark: | :white_check_mark:  |
 
<small><sup>1</sup> Special meter entity. It counts burned fuel when HomeAssistant is running.</small><br>
<small><sup>2</sup> Controller support is required.</small><br>
<small><sup>3</sup> ecoLAMBDA module is required.</small>

#### Binary sensors
Binary sensors have two states (on/off, running/not running, etc.).

| Name                    | ecoMAX pellet      | ecoMAX installation |
|-------------------------|:------------------:|:-------------------:|
| Heating pump state      | :white_check_mark: | :white_check_mark:  |
| Water heater pump state | :white_check_mark: | :white_check_mark:  |
| Circulation pump state  | :white_check_mark: | :white_check_mark:  |
| Fireplace pump state    | :x:                | :white_check_mark:  |
| Solar pump state        | :x:                | :white_check_mark:  |
| Fan state               | :white_check_mark: | :x:                 |
| Lighter state           | :white_check_mark: | :x:                 |
| Exhaust fan state       | :white_check_mark: | :x:                 |

#### Switches
Switches have two states (on/off) that can be switched between.

| Name                             | ecoMAX pellet      | ecoMAX installation |
|----------------------------------|:------------------:|:-------------------:|
| Controller power switch          | :white_check_mark: | :white_check_mark:  |
| Water heater disinfection switch | :white_check_mark: | :white_check_mark:  |
| Water heater pump switch         | :white_check_mark: | :white_check_mark:  |
| Summer mode switch               | :white_check_mark: | :white_check_mark:  |
| Weather control switch           | :white_check_mark: | :x:                 |
| Fuzzy logic switch               | :white_check_mark: | :x:                 |
| Heating schedule switch          | :white_check_mark: | :x:                 |
| Water heater schedule switch     | :white_check_mark: | :x:                 |

#### Numbers
Numbers are represented as changeable sliders or input boxes.

| Name                        | Unit   | Style  | ecoMAX pellet      | ecoMAX installation |
|-----------------------------|:------:|:------:|:------------------:|:-------------------:|
| Heating temperature         | °C     | slider | :white_check_mark: | :x:                 |
| Minimum heating power       | %      | slider | :white_check_mark: | :x:                 |
| Maximum heating power       | %      | slider | :white_check_mark: | :x:                 |
| Minimum heating temperature | °C     | slider | :white_check_mark: | :x:                 |
| Maximum heating temperature | °C     | slider | :white_check_mark: | :x:                 |
| Grate mode temperature      | °C     | slider | :white_check_mark: | :x:                 |
| Fuel calorific value        | kWh/kg | box    | :white_check_mark: | :x:                 |

#### Diagnostics
Diagnostics are random entities that provide you with service and debug information.

| Name               | Type          | ecoMAX pellet      | ecoMAX installation |
|--------------------|:-------------:|:------------------:|:-------------------:|
| Alert              | Binary sensor | :white_check_mark: | :white_check_mark:  |
| Connection status  | Binary sensor | :white_check_mark: | :white_check_mark:  |
| Service password   | Text sensor   | :white_check_mark: | :white_check_mark:  |
| UID                | Text sensor   | :white_check_mark: | :white_check_mark:  |
| Software version   | Text sensor   | :white_check_mark: | :white_check_mark:  |
| Detect sub-devices | Button        | :white_check_mark: | :white_check_mark:  |

### Water heater
The integration provides full control for the connected indirect water heater using Home Assistant's [internal water heater platform](https://www.home-assistant.io/integrations/water_heater/).

This includes ability to set target temperature, switch into priority, non-priority mode or turn off.

Please note, that due to the way base water heater entity is implemented,
custom modes [are not allowed](https://developers.home-assistant.io/docs/core/entity/water-heater/#states).
Please use the following reference table to convert between water heater operation modes displayed in Home Assistant and ecoMAX.

| HomeAssistant  | ecoMAX            |
|----------------|-------------------|
| Off            | On                |
| Performance    | Priority mode     |
| Eco            | Non-priority mode |

### Thermostats
This integration provides Home Assistant's [climate platform](https://www.home-assistant.io/integrations/climate/) entity for each ecoSTER thermostat connected to the ecoMAX controller.

This allows to check current room temperature, set target room temperature and change between ecoSTER operation modes.

![Climate card](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/climate-card.png)

### Mixers/Circuits (Sub-devices)
Following section lists entities that are added to each sub-device.

Please note, that for ecoMAX installation ("**i**") controllers mixers are renamed to circuits.

Mixers/Circuits are added as sub-devices for the ecoMAX controller.<br>
Sub-devices detected only once, when integration is added to HomeAssistant.<br>
If you connected them after setting up the integration, you can use `Detect sub-devices` button in Diagnostics section and then reload integration to force detection of new sub-devices.

### Sensors

| Name                      | Unit | ecoMAX pellet      | ecoMAX installation |
|---------------------------|:----:|:------------------:|:-------------------:|
| Mixer temperature         | °C   | :white_check_mark: | :white_check_mark:  |
| Target mixer temperature  | °C   | :white_check_mark: | :white_check_mark:  |


#### Binary sensors

| Name       | ecoMAX pellet      | ecoMAX installation |
|------------|:------------------:|:-------------------:|
| Mixer pump | :white_check_mark: | :white_check_mark:  |

#### Switches
| Name                                 | ecoMAX pellet      | ecoMAX installation |
|--------------------------------------|:------------------:|:-------------------:|
| Enable in summer mode                | :white_check_mark: | :white_check_mark:  |
| Enable mixer                         | :x:                | :white_check_mark:  |
| Weather control                      | :white_check_mark: | :x:                 |
| Disable pump on thermostat           | :white_check_mark: | :x:                 |

#### Numbers

| Name                                        | Unit | Style  | ecoMAX pellet      | ecoMAX installation |
|---------------------------------------------|:----:|:------:|:------------------:|:-------------------:|
| Mixer temperature                           | °C   | slider | :white_check_mark: | :white_check_mark:  |
| Minimum mixer temperature                   | °C   | slider | :white_check_mark: | :white_check_mark:  |
| Maximum mixer temperature                   | °C   | slider | :white_check_mark: | :white_check_mark:  |
| Day target mixer temperature <sup>1</sup>   | °C   | slider | :x:                | :white_check_mark:  |
| Night target mixer temperature <sup>1</sup> | °C   | slider | :x:                | :white_check_mark:  |

<small><sup>1</sup> Only available on second circuit.</small>

## Services
This integration provides following services:

### Set parameter
Provides ability to set device/sub-device parameter by name. Any parameter that is supported by the device/sub-device can be used with this service. To get parameter names, please download and open diagnostics data.

#### Fields

| Field | Type                | Description             |
|-------|---------------------|-------------------------|
| name  | string              | Name of the parameter.  |
| value | number, "on", "off" | Value of the parameter. |

#### Targets

| Device <sup>1</sup> | Description                             |
|---------------------|-----------------------------------------|
| ecoMAX              | Set parameter on the ecoMAX controller. |
| Mixer               | Set parameter on the mixer sub-device.  |

<small><sup>1</sup> Device can be targeted via any selector: area, device or entity.</small>


### Calibrate meter
Allows to set meter entity to a specific value.<br>
Currently this can be used to set a value of a `Total fuel burned` sensor which is only available on pellet burner controllers.

#### Fields
| Field  | Type    | Description                       |
|--------|---------|-----------------------------------|
| value  | integer | Set target sensor to this value.  |

#### Targets
| Entity            | Description                            |
|-------------------|----------------------------------------|
| total_fuel_burned | Counts total burned fuel in kilograms. |


### Reset meter
Allows to reset the meter entity value.<br>
Currently this can be used to reset a value of the `Total fuel burned` sensor which is only available on pellet burner controllers.

#### Targets
| Entity            | Description                            |
|-------------------|----------------------------------------|
| total_fuel_burned | Counts total burned fuel in kilograms. |

## License
This product is distributed under MIT license.
