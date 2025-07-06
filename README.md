# Plum ecoMAX boiler controller integration for Home Assistant

[![ci](https://github.com/denpamusic/homeassistant-plum-ecomax/actions/workflows/ci.yml/badge.svg)](https://github.com/denpamusic/homeassistant-plum-ecomax/actions/workflows/ci.yml)
[![Code Coverage](https://qlty.sh/badges/8f2f6d2d-8811-4cea-aade-cb563c0fada0/test_coverage.svg)](https://qlty.sh/gh/denpamusic/projects/homeassistant-plum-ecomax)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![stability-release-candidate](https://img.shields.io/badge/stability-pre--release-48c9b0.svg)](https://guidelines.denpa.pro/stability#release-candidate)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Overview

This Home Assistant integration provides support for ecoMAX controllers
manufactured by [Plum Sp. z o.o.](https://www.plum.pl/)

It's based on [PyPlumIO](https://github.com/denpamusic/PyPlumIO) package
and supports connection to ecoMAX controller via RS-485 to Ethernet/Wifi
converters or via RS-485 to USB adapter.

![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/ecomax.png)

## Table of contents

- [Connect the ecoMAX](#connect-the-ecomax)
- [Installation](#installation)
  - [HACS](#hacs)
  - [Manual](#manual)
- [Configuration](#configuration)
- [Entities](#entities)
  - [Controller](#controller-hub)
  - [Water Heater](#water-heater)
  - [Thermostats](#thermostats)
  - [Mixers](#mixers-circuits)
- [Events](#events)
- [Actions](#actions)
- [License](#license)

## Connect the ecoMAX

With this integration you have two ways of connecting to your ecoMAX
controller. One is directly connecting the PC that runs Home Assistant
via **RS485 to USB adapter**.

Other way is to use **RS485 to WiFi converter**. This has a benefit of being
able to move PC that runs Home Assistant away from the boiler and connect
to it wirelessly.

![RS485 adapter and converters](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/rs485.png)

Regardless of the chosen method, you'll need to find RS485 port on your ecoMAX controller.
If you have ecoSTER thermostat, it's easy, as ecoSTERs also use RS485 port and
you'll just have to connect your adapter/converter in parallel with it.

If you don't have ecoSTER, look for pins that are labeled as "D+" and
"D-" then connect your device as follows:

```plaintext
Adapter ->  ecoMAX
[A]     ->  [D+]
[B]     ->  [D-]
[GND]   ->  [GND] (optional, less interference)
```

### ecoNET 300

While this integration is built on top of PyPlumIO library, which from the
start was intended as ecoNET 300 alternative, **Patryk B** has originally
developed awesome HASS integration that communicates with ecoMAX controller
via ecoNET 300 device.

Development of this integration has recently been picked up by @jontofront,
so it's getting regular updates and fixes again!
If you have an ecoNET 300 device, be sure to
[check it out](https://github.com/jontofront/ecoNET-300-Home-Assistant-Integration)!

## Installation

### HACS

Click the following My button to install the integration via HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=denpamusic&repository=homeassistant-plum-ecomax&category=integration)

HACS is **recommended** method to install and update the
plum-ecomax integration.  
If you still don't use it, give it a try, I'm sure you'll love it!

### Manual

1. Clone this repository with:

```sh
git clone https://github.com/denpamusic/homeassistant-plum-ecomax
```

2. Move `custom_components` directory from `homeassistant-plum-ecomax` to
   your Home Assistant configuration directory. ([next to configuration.yaml](https://www.home-assistant.io/docs/configuration/))

```sh
cp -r ./homeassistant-plum-ecomax/custom_components ~/.homeassistant
```

3. Restart Home Assistant.

## Configuration

Adding Plum ecoMAX integration to your Home Assistant instance can be
done via user interface, by using this My button:

[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=plum_ecomax)

<details>
  <summary><b>Manual configuration</b> <i>(click to expand)</i></summary>

If the above My button doesn’t work, you can also perform the following steps manually:

1. Browse to your Home Assistant instance.
2. In the sidebar click on Settings.
3. From the configuration menu select: Devices & Services.
4. In the bottom right, click on the Add Integration button.
5. From the list, search and select "Plum ecoMAX".

![Search dialog](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/search.png)

6. Select you connection type. Choose serial port if your ecoMAX controller
   is connected directly to the PC that is running Home Assistant, choose
   network if ecoMAX is connected via RS-485 to WiFi converter

![Menu](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/menu.png)

To connect via the network you'll need to fill in Host and Port:

![TCP](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/tcp.png)

To connect via serial port you'll need to fill in the Device path and Baudrate:

![serial](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/serial.png)

> :warning: If you're running your Home Assistant in the docker container,
> don't forget to map your adapter/converter device, as described
> [here](https://www.home-assistant.io/installation/raspberrypi#exposing-devices).

7. Your device should now be available in your Home Assistant installation.

![Success](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/success.png)

</details>

## Entities

This integration provides the following entities, split between controller
device and sub-devices.

Not all entities might be available for your controller model and entities
that are deemed as unsupported during initial setup will be disabled.

ecoMAX pellet boiler controller model names has a <kbd>p</kbd> suffix
(e. g. ecoMAX 850**p**), while ecoMAX installation controller model names
have an <kbd>i</kbd> suffix (e. g. ecoMAX 850**i**).

### Controller

The following section lists entities that are added to the ecoMAX device.

Legend:

- <kbd>i</kbd> - ecoMAX installation controller
- <kbd>p</kbd> - ecoMAX pellet boiler controller

---

<details>
  <summary><b>🌡️Sensors</b> <i>(click to expand)</i></summary><br>

> ℹ️ Temperature changes of **less than 0.1°C** are ignored.

- Heating temperature
- Water heater temperature
- Outside temperature
- Heating target temperature
- Water heater target temperature
- Heating mode
- Exhaust temperature
- Feeder temperature
- Return temperature
- Heating load
- Fan power
- Fuel level
- Fuel consumption
- Total fuel burned <sup>1</sup>
- Heating power
- Lower buffer temperature <sup>2</sup>
- Upper buffer temperature <sup>2</sup>
- Flame intensity <sup>2</sup>
- Lower buffer temperature <sup>2</sup>
- Upper buffer temperature <sup>2</sup>
- Flame intensity <sup>2</sup>
- Oxygen level <sup>3</sup>
- Solar temperature <kbd>i</kbd>
- Fireplace temperature <kbd>i</kbd>

<sup>1</sup> _Special meter entity. It counts burned fuel when
HomeAssistant is running._  
<sup>2</sup> _Controller support is required._  
<sup>3</sup> _ecoLAMBDA module is required._

</details>
<details>
  <summary><b>🔛Binary sensors</b> <i>(click to expand)</i></summary>

- Heating pump state
- Water heater pump state
- Circulation pump state
- Fan state
- Lighter state
- Exhaust fan state
- Fireplace pump state <kbd>i</kbd>
- Solar pump state <kbd>i</kbd>

</details>
<details>
  <summary><b>✅Selects</b> <i>(click to expand)</i></summary>

- Summer mode (on, off, auto)

</details>
<details>
  <summary><b>💡Switches</b> <i>(click to expand)</i></summary>

- Controller power switch
- Water heater disinfection switch
- Water heater pump switch
- Weather control switch <kbd>p</kbd>
- Fuzzy logic switch <kbd>p</kbd>
- Heating schedule switch <kbd>p</kbd>
- Water heater schedule switch <kbd>p</kbd>

</details>
<details>
  <summary><b>🔢Numbers</b> <i>(click to expand)</i></summary>

- Heating temperature <kbd>p</kbd>
- Minimum heating power <kbd>p</kbd>
- Maximum heating power <kbd>p</kbd>
- Minimum heating temperature <kbd>p</kbd>
- Maximum heating temperature <kbd>p</kbd>
- Grate mode temperature <kbd>p</kbd>
- Fuel calorific value <kbd>p</kbd>

</details>

<details>
  <summary><b>🛠️Diagnostics</b> <i>(click to expand)</i></summary>

- Alert
- Connection status
- Service password
- Connected modules
- Detect sub-devices

</details>

### Water heater

The integration provides full control for the connected indirect water
heater using Home Assistant's
[internal water heater platform](https://www.home-assistant.io/integrations/water_heater/).

This includes ability to set target temperature, switch into priority,
non-priority mode or turn off.

Please note, that due to the way base water heater entity is implemented,
custom modes [are not allowed](https://developers.home-assistant.io/docs/core/entity/water-heater/#states).

Please use the following reference to convert between water heater operation
modes displayed in Home Assistant and ecoMAX.

```plaintext
HA heater state ->  ecoMAX heater mode
[Performance]   ->  [Priority mode]
[Eco]           ->  [Non-priority mode]
```

### Thermostats

This integration provides Home Assistant's
[climate platform](https://www.home-assistant.io/integrations/climate/)
entity for each ecoSTER thermostat connected to the ecoMAX controller.

This allows to check current room temperature, set target room temperature
and change between ecoSTER operation modes.

![Climate card](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/climate-card.png)

### Mixers (Circuits)

Following section lists entities that are added to each virtual device.

Please note, that for the ecoMAX installation controllers `mixers` are
listed as `circuits`.

Mixers are added as sub-devices for the ecoMAX controller.
They are detected only once, when integration is added to HomeAssistant.

If you connected them after setting up the integration, you can use
`Detect sub-devices` button in Diagnostics section to force re-detection.

Legend:

- <kbd>i</kbd> - ecoMAX installation controller
- <kbd>p</kbd> - ecoMAX pellet boiler controller

---

<details>
  <summary><b>🌡️Sensors</b> <i>(click to expand)</i></summary>

- Mixer temperature
- Target mixer temperature

</details>
<details> <summary><b>🔛Binary sensors</b> <i>(click to expand)</i></summary>

- Mixer pump

</details>
<details> <summary><b>✅Selects</b> <i>(click to expand)</i></summary>

- Work mode (off, heating, floor, pump_only) <kbd>p</kbd>

</details>
<details> <summary><b>💡Switches</b> <i>(click to expand)</i></summary>

- Enable mixer <kbd>i</kbd>
- Enable in summer mode
- Weather control <kbd>p</kbd>
- Disable pump on thermostat <kbd>p</kbd>

</details>
<details> <summary><b>🔢Numbers</b> <i>(click to expand)</i></summary>

- Mixer temperature
- Minimum mixer temperature
- Maximum mixer temperature
- Day target mixer temperature <sup>1</sup> <kbd>i</kbd>
- Night target mixer temperature <sup>1</sup> <kbd>i</kbd>

<sup>1</sup> _Only available on second circuit._

</details>

## Events

The integration uses following events:

### plum_ecomax_alert

Event is fired when ecoMAX controller issues an alert.

#### Event data

- name (config entry name)
- code (alert code)
- from (datetime object representing the alert start time)
- to <sup>1</sup> (datetime object representing the alert end time)

<sup>1</sup> _Only present if the alert has already ended._

## Actions

This integration provides following actions:

### Get parameter

Provides ability to get the device parameter by name.

#### Fields

- name

#### Targets

- ecomax
- mixer

#### Response

- name
- value
- min_value
- max_value
- device_type
- device_uid
- device_index <sup>1</sup>

<sup>1</sup> _This will help identify which sub-device (mixer) this
parameter belongs to. Root device (controller) is always 0, while
connected mixers can have 1-5._

### Set parameter

Provides ability to set device/sub-device parameter by name.
Any parameter that is supported by the device/sub-device can be used with
this service. To get parameter names, please download and open diagnostics data.

#### Set parameter fields

- name
- value

#### Set parameter targets

- ecomax
- mixer

### Get schedule

Allows to get different schedules from the device.

#### Get schedule fields

- type (heating, water_heater)
- weekdays (monday, tuesday, ..., etc)

#### Get schedule response

- schedules (dictionary containing schedule states, keyed by start times)

### Set schedule

Allows to set different schedules on the device.

#### Set schedule fields

- type (heating, water_heater)
- weekdays (monday, tuesday, ..., etc)
- preset (day, night)
- start
- end

### Calibrate meter

Allows to set meter entity to a specific value. This can be used to set a
value of a `Total fuel burned` sensor which is only available on
pellet burner controllers.

#### Calibrate meter fields

- value

#### Calibrate meter targets

- total_fuel_burned

### Reset meter

Allows to reset the meter entity value. This can be used to reset a
value of the `Total fuel burned` sensor which is only available on
pellet burner controllers.

#### Reset meter targets

- total_fuel_burned

## License

This product is distributed under MIT license.
