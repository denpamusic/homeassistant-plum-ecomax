"""Constants for the Plum ecoMAX integration."""

from enum import StrEnum, unique
from typing import Final

DOMAIN = "plum_ecomax"
MANUFACTURER: Final = "Plum Sp. z o.o."

# Generic attributes.
ATTR_ENTITIES: Final = "entities"
ATTR_FROM: Final = "from"
ATTR_MIXERS: Final = "mixers"
ATTR_MODULES: Final = "modules"
ATTR_PASSWORD: Final = "password"
ATTR_PRODUCT: Final = "product"
ATTR_REGDATA: Final = "regdata"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_TO: Final = "to"
ATTR_VALUE: Final = "value"
ATTR_WATER_HEATER: Final = "water_heater"
ATTR_WEEKDAYS: Final = "weekdays"

# Baudrates.
# (should be listed as strings due to the visual bug in hass selectors)
BAUDRATES: Final[tuple[str, ...]] = (
    "9600",
    "14400",
    "19200",
    "38400",
    "57600",
    "115200",
)

# Weekdays.
WEEKDAYS: Final[tuple[str, ...]] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

# Configuration flow.
CONF_BAUDRATE: Final = "baudrate"
CONF_CAPABILITIES: Final = "capabilities"
CONF_CONNECTION_TYPE: Final = "connection_type"
CONF_DEVICE: Final = "device"
CONF_HOST: Final = "host"
CONF_KEY: Final = "key"
CONF_MODEL: Final = "model"
CONF_PORT: Final = "port"
CONF_PRODUCT_ID: Final = "product_id"
CONF_PRODUCT_TYPE: Final = "product_type"
CONF_SOFTWARE: Final = "software"
CONF_SOURCE_DEVICE: Final = "source_device"
CONF_STEP: Final = "step"
CONF_SUB_DEVICES: Final = "sub_devices"
CONF_UID: Final = "uid"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Connection types.
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPE_TCP: Final = "TCP"

# Defaults.
DEFAULT_BAUDRATE: Final = BAUDRATES[-1]
DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"
DEFAULT_PORT: Final = 8899
DEFAULT_TOLERANCE: Final = 0.1

# Events.
EVENT_PLUM_ECOMAX_ALERT: Final = "plum_ecomax_alert"

# Units.
FLOW_KG_H: Final = "kg/h"

# Extended parameters.
ATTR_CONTROL_MODE: Final = "control_mode"

# Legacy parameters that hold the same setting as an extended parameter,
# keyed by the legacy key. Legacy entities are not created when the
# extended parameter is available.
EXTENDED_PARAMETER_REPLACEMENTS: Final[dict[str, str]] = {
    "airflow_power_100": "fan_speed_100",
    "airflow_power_50": "fan_speed_50",
    "airflow_power_30": "fan_speed_30",
    "boiler_alert_temp": "boiler_cooling_temp",
    "burning_off_airflow_power": "burning_off_fan_speed",
    "burning_off_min_time": "min_burning_off_duration",
    "fuel_detection_time": "no_fuel_detection_time",
    "fuzzy_logic": ATTR_CONTROL_MODE,
    "heating_pump_enable_temp": "heating_pump_start_temp",
    "kindling_min_power_time": "glowing_duration",
    "kindling_test_time": "ignition_test_time",
    "kindling_airflow_power": "kindling_fan_speed",
    "kindling_time": "kindling_duration",
    "max_fan_power": "max_fan_output",
    "max_heating_target_temp": "max_boiler_target_temp",
    "min_fan_power": "min_fan_output",
    "min_heating_target_temp": "min_boiler_target_temp",
    "stabilization_airflow_power": "stabilization_fan_speed",
    "supervision_airflow_power": "supervision_fan_speed",
    "supervision_time": "supervision_duration",
    "thermostat_decrease_target_temp": "thermostat_decrease_boiler_temp",
    "warming_up_pause_time": "burner_cleaning_interval",
    "warming_up_time": "warming_up_duration",
}


@unique
class DeviceType(StrEnum):
    """Known devices, represented by PyPlumIO's Device class."""

    ECOMAX = "ecomax"
    MIXER = "mixer"
    THERMOSTAT = "thermostat"


LOGICAL_DEVICES: Final = (DeviceType.MIXER, DeviceType.THERMOSTAT)


@unique
class ModuleType(StrEnum):
    """Known ecoMAX modules."""

    A = "module_a"
    B = "module_b"
    C = "module_c"
    ECOLAMBDA = "ecolambda"
    ECOSTER = "ecoster"
    PANEL = "panel"
