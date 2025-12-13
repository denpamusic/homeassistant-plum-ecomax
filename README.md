# Plum ecoMAX boiler controller integration for Home Assistant

[![ci](https://github.com/denpamusic/homeassistant-plum-ecomax/actions/workflows/ci.yml/badge.svg)](https://github.com/denpamusic/homeassistant-plum-ecomax/actions/workflows/ci.yml)
[![Code Coverage](https://qlty.sh/gh/denpamusic/projects/homeassistant-plum-ecomax/coverage.svg)](https://qlty.sh/gh/denpamusic/projects/homeassistant-plum-ecomax)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![stability-release-candidate](https://img.shields.io/badge/stability-pre--release-48c9b0.svg)](https://guidelines.denpa.pro/stability#release-candidate)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 📖 Overview

This Home Assistant integration provides support for ecoMAX controllers manufactured by [Plum Sp. z o.o.](https://www.plum.pl/).

It uses the [PyPlumIO](https://github.com/denpamusic/PyPlumIO) library and supports connection to ecoMAX controllers via RS-485 over Ethernet/Wi‑Fi converters or RS-485 to USB adapters.

![ecoMAX controllers](https://raw.githubusercontent.com/denpamusic/homeassistant-plum-ecomax/main/images/ecomax.png)

## 📑 Table of contents

- [Connect the ecoMAX](#connect-the-ecomax)
- [Installation](#-installation)
  - [HACS](#hacs)
  - [Manual](#manual)
- [Configuration](#-configuration)
- [Entities](#-entities)
  - [Controller](#controller-hub)
  - [Water Heater](#-water-heater)
  - [Thermostats](#-thermostats)
  - [Mixers](#-mixers-circuits)
- [Events](#-events)
- [Actions](#-actions)
- [License](#-license)

## 🔌 Connect the ecoMAX

You can connect your ecoMAX controller in two ways:

- Directly to the machine running Home Assistant using an RS-485 to USB adapter.
- Wirelessly via an RS-485 to Wi‑Fi converter so the Home Assistant host can be remote from the boiler.

Locate the RS-485 terminal on the ecoMAX (pins labeled "D+" and "D-") and wire your adapter as follows:

| Adapter | ecoMAX |
|---:|:---|
| A | D+ |
| B | D- |
| GND | GND (optional) |

### ecoNET 300

This integration is built upon the PyPlumIO library, which was originally designed as an alternative to the ecoNET 300 device. For users who possess the original ecoNET 300 from Plum, **Patryk B** has developed an excellent Home Assistant integration.

The development of this ecoNET 300 integration has been resumed by **jontofront**, ensuring that it receives regular updates and fixes. If you own an ecoNET 300 device, I encourage you to [explore this integration](https://github.com/jontofront/ecoNET-300-Home-Assistant-Integration).

## 📦 Installation

### HACS

HACS is the recommended installation method. Click the button below to install via HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=denpamusic&repository=homeassistant-plum-ecomax&category=integration)

### Manual

<details>
<summary><b>Manual installation</b> <i>(click to expand)</i></summary>

1. Clone the repository:

```sh
git clone https://github.com/denpamusic/homeassistant-plum-ecomax
```

2. Copy the `custom_components` directory to your Home Assistant configuration folder (next to configuration.yaml):

```sh
cp -r ./homeassistant-plum-ecomax/custom_components ~/.homeassistant
```

3. Restart Home Assistant.

</details>

## ⚙️ Configuration

Add the Plum ecoMAX integration from Home Assistant's UI:

Settings → Devices & Services → Add Integration → search for "Plum ecoMAX".

Choose the connection type:

- Network (RS-485 to Wi‑Fi): provide Host and Port.
- Serial: provide Device path and Baudrate.

If running Home Assistant in Docker, ensure the adapter device is mapped into the container.

## 🏠 Entities

The integration exposes entities on the main controller device and its sub-devices. Available entities depend on your controller model and connected modules. Unsupported entities will be disabled during setup.

Note: ecoMAX pellet boiler controller model names use a "p" suffix (e.g., ecoMAX 850p), while installation controllers use an "i" suffix (e.g., ecoMAX 850i).

**Legend:**
- <kbd>i</kbd> — ecoMAX installation controller
- <kbd>p</kbd> — ecoMAX pellet boiler controller


### 🔥 Controller

<details>
<summary><b>Sensors</b> <i>(click to expand)</i></summary>

Sensors (temperature changes < 0.1°C ignored):
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
- Total fuel burned¹
- Heating power
- Lower buffer temperature²
- Upper buffer temperature²
- Flame intensity²
- Oxygen level³
- Solar temperature <kbd>i</kbd>
- Fireplace temperature <kbd>i</kbd>

¹ Meter entity: counts burned fuel while Home Assistant runs.  
² Requires controller support.  
³ Requires ecoLAMBDA module.

</details>

<details>
<summary><b>Binary sensors</b> <i>(click to expand)</i></summary>

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
<summary><b>Selects</b> <i>(click to expand)</i></summary>

- Summer mode (on, off, auto)

</details>

<details>
<summary><b>Switches</b> <i>(click to expand)</i></summary>

- Controller power
- Water heater disinfection
- Water heater pump
- Weather control <kbd>p</kbd>
- Fuzzy logic <kbd>p</kbd>
- Heating schedule <kbd>p</kbd>
- Water heater schedule <kbd>p</kbd>

</details>

<details>
<summary><b>Numbers</b> <i>(click to expand)</i></summary>

- Heating temperature <kbd>p</kbd>
- Minimum heating power <kbd>p</kbd>
- Maximum heating power <kbd>p</kbd>
- Minimum heating temperature <kbd>p</kbd>
- Maximum heating temperature <kbd>p</kbd>
- Grate mode temperature <kbd>p</kbd>
- Fuel calorific value <kbd>p</kbd>

</details>

<details>
<summary><b>Diagnostics</b> <i>(click to expand)</i></summary>

- Alert
- Connection status
- Service password
- Connected modules
- Detect sub-devices

</details>

### 💧 Water heater

The integration provides a Home Assistant water heater entity for indirect water heaters. You can set target temperature, toggle priority mode, or turn the heater off.

Home Assistant heater states map to ecoMAX modes:

| Home Assistant Heater State | ecoMAX Heater Mode |
|----------------------------:|--------------------:|
| Performance                 | Priority Mode       |
| Eco                         | Non-Priority Mode   |

### 🌡️ Thermostats

Each connected ecoSTER thermostat is exposed as a Home Assistant climate entity, allowing monitoring and control of room temperature and ecoSTER modes.

### 🔀 Mixers (Circuits)

Mixers (called circuits on installation controllers) are logical devices detected once when the integration is added.

Sensors:
- Mixer temperature
- Mixer target temperature

Binary sensors:
- Mixer pump

Selects:
- Work mode (off, heating, floor, pump_only) <kbd>p</kbd>

Switches:
- Enable mixer <kbd>i</kbd>
- Enable in summer mode
- Weather control <kbd>p</kbd>
- Disable pump on thermostat <kbd>p</kbd>

Numbers:
- Mixer temperature
- Minimum mixer temperature
- Maximum mixer temperature
- Day target mixer temperature <kbd>i</kbd> — second circuit only
- Night target mixer temperature <kbd>i</kbd> — second circuit only

## 📢 Events

The integration uses the following events:

### plum_ecomax_alert

Fired when the ecoMAX controller issues an alert.

**Event data:**
- `name` — Config entry name
- `code` — Alert code
- `from` — Datetime object representing alert start time
- `to` <sup>1</sup> — Datetime object representing alert end time

<sup>1</sup> _Only present if the alert has ended._

---

## ⚙️ Actions

This integration provides the following actions:

### 🔍 Get parameter

Retrieve a device parameter by name.

**Fields:** `name`  
**Targets:** `ecomax`, `mixer`

**Response:**
- `name` — Parameter name
- `value` — Parameter value
- `min_value` — Minimum allowed value
- `max_value` — Maximum allowed value
- `device_type` — Device type
- `device_uid` — Device unique identifier
- `device_index` <sup>1</sup> — Sub-device identifier

<sup>1</sup> _Root device (controller) is 0; connected mixers are 1–5._

### 📝 Set parameter

Set a device/sub-device parameter by name.

**Fields:** `name`, `value`  
**Targets:** `ecomax`, `mixer`

### 📅 Get schedule

Retrieve schedules from the device.

**Fields:** `type` (heating, water_heater), `weekdays` (monday, tuesday, etc.)

**Response:** `schedules` — Dictionary of schedule states keyed by start times

### 📅 Set schedule

Configure device schedules.

**Fields:** `type` (heating, water_heater), `weekdays`, `preset` (day, night), `start`, `end`

### 📊 Calibrate meter

Set a meter entity to a specific value.

**Fields:** `value`  
**Targets:** `total_fuel_burned`

### 🔄 Reset meter

Reset a meter entity value.

**Targets:** `total_fuel_burned`

## 📄 License

This product is distributed under MIT license.

