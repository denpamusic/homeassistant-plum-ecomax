"""Constants for the Plum ecoMAX integration."""

from enum import StrEnum, unique
from typing import Final

DOMAIN = "plum_ecomax"
MANUFACTURER: Final = "Plum Sp. z o.o."

# Generic constants.
ALL: Final = "all"

# Generic attributes.
ATTR_ALERTS: Final = "alerts"
ATTR_ECOMAX_CONTROL: Final = "ecomax_control"
ATTR_ECOMAX_PARAMETERS: Final = "ecomax_parameters"
ATTR_END: Final = "end"
ATTR_FROM: Final = "from"
ATTR_LOADED: Final = "loaded"
ATTR_MIXERS: Final = "mixers"
ATTR_MIXER_PARAMETERS: Final = "mixer_parameters"
ATTR_MODULES: Final = "modules"
ATTR_NUMERIC: Final = "numeric"
ATTR_PASSWORD: Final = "password"
ATTR_PRODUCT: Final = "product"
ATTR_PRESET: Final = "preset"
ATTR_SCHEDULES: Final = "schedules"
ATTR_SENSORS: Final = "sensors"
ATTR_START: Final = "start"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_THERMOSTAT_PARAMETERS: Final = "thermostat_parameters"
ATTR_TO: Final = "to"
ATTR_TYPE: Final = "type"
ATTR_VALUE: Final = "value"
ATTR_WATER_HEATER: Final = "water_heater"
ATTR_WATER_HEATER_TEMP: Final = "water_heater_temp"
ATTR_WEEKDAYS: Final = "weekdays"
ATTR_FIRMWARE: Final = "firmware"
ATTR_REGDATA: Final = "regdata"

# Devices.
ECOMAX: Final = "ecomax"
ECOLAMBDA: Final = "ecolambda"
ECOSTER: Final = "ecoster"

# Modules.
MODULE_A: Final = "module_a"
MODULE_B: Final = "module_b"
MODULE_C: Final = "module_c"

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
CONF_CAPABILITIES: Final = "capabilities"
CONF_CONNECTION_TYPE: Final = "connection_type"
CONF_DEVICE: Final = "device"
CONF_BAUDRATE: Final = "baudrate"
CONF_HOST: Final = "host"
CONF_MODEL: Final = "model"
CONF_PORT: Final = "port"
CONF_PRODUCT_TYPE: Final = "product_type"
CONF_PRODUCT_ID: Final = "product_id"
CONF_SOFTWARE: Final = "software"
CONF_SUB_DEVICES: Final = "sub_devices"
CONF_TITLE: Final = "title"
CONF_UID: Final = "uid"

# Connection types.
CONNECTION_TYPE_TCP: Final = "TCP"
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPES: Final = (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL)

# Defaults.
DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"
DEFAULT_BAUDRATE: Final = BAUDRATES[-1]
DEFAULT_PORT: Final = 8899

# Units of measurement.
CALORIFIC_KWH_KG: Final = "kWh/kg"
FLOW_KGH: Final = "kg/h"

# Events.
EVENT_PLUM_ECOMAX_ALERT: Final = "plum_ecomax_alert"

# Device classes.
DEVICE_CLASS_STATE: Final = "plum_ecomax__state"
DEVICE_CLASS_METER: Final = "plum_ecomax__meter"


# Device models.
@unique
class ProductModel(StrEnum):
    """Contains known device models."""

    ECOMAX_350P2_ZF = "ecoMAX 350P2-ZF"
    ECOMAX_850I = "ecoMAX 850i"
    ECOMAX_850P2_C = "ecoMAX 850P2-C"
    ECOMAXX_800R3 = "ecoMAXX 800R3"
    ECOMAX_860D3_HB = "ecoMAX 860D3-HB"
    ECOMAX_860P3_O = "ecoMAX 860P3-O"
    ECOMAX_860P3_S_LITE = "ecoMAX 860P3-S LITE"
    ECOMAX_920P1_O = "ecoMAX920 P1-O"
