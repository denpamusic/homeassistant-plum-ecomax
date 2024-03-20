"""Constants for the Plum ecoMAX integration."""

from enum import StrEnum, unique
from typing import Final

DOMAIN = "plum_ecomax"

# Generic constants.
ALL: Final = "all"
MANUFACTURER: Final = "Plum Sp. z o.o."

# Generic attributes.
ATTR_BURNED_SINCE_LAST_UPDATE: Final = "burned_since_last_update"
ATTR_END: Final = "end"
ATTR_FIRMWARE: Final = "firmware"
ATTR_FROM: Final = "from"
ATTR_LOADED: Final = "loaded"
ATTR_MIXERS: Final = "mixers"
ATTR_MODULES: Final = "modules"
ATTR_NUMERIC_STATE: Final = "numeric_state"
ATTR_PASSWORD: Final = "password"
ATTR_PRESET: Final = "preset"
ATTR_PRODUCT: Final = "product"
ATTR_REGDATA: Final = "regdata"
ATTR_SCHEDULES: Final = "schedules"
ATTR_SENSORS: Final = "sensors"
ATTR_START: Final = "start"
ATTR_THERMOSTATS: Final = "thermostats"
ATTR_TO: Final = "to"
ATTR_TYPE: Final = "type"
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
CONF_KEY: Final = "key"
CONF_DEVICE: Final = "device"
CONF_HOST: Final = "host"
CONF_MODEL: Final = "model"
CONF_PORT: Final = "port"
CONF_PRODUCT_ID: Final = "product_id"
CONF_PRODUCT_TYPE: Final = "product_type"
CONF_SOFTWARE: Final = "software"
CONF_SUB_DEVICES: Final = "sub_devices"
CONF_TITLE: Final = "title"
CONF_UID: Final = "uid"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Connection types.
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPE_TCP: Final = "TCP"
CONNECTION_TYPES: Final = (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL)

# Defaults.
DEFAULT_BAUDRATE: Final = BAUDRATES[-1]
DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"
DEFAULT_PORT: Final = 8899

# Units of measurement.
CALORIFIC_KWH_KG: Final = "kWh/kg"
FLOW_KGH: Final = "kg/h"

# Events.
EVENT_PLUM_ECOMAX_ALERT: Final = "plum_ecomax_alert"

# Device classes.
DEVICE_CLASS_STATE: Final = "plum_ecomax__state"
DEVICE_CLASS_METER: Final = "plum_ecomax__meter"

# Data registry.
REGDATA = "regdata"


@unique
class DeviceType(StrEnum):
    """Known devices, represented by PyPlumIO's Device class."""

    ECOMAX = "ecomax"
    MIXER = "mixer"
    THERMOSTAT = "thermostat"


@unique
class ModuleType(StrEnum):
    """Known ecoMAX modules."""

    A = "module_a"
    B = "module_b"
    C = "module_c"
    ECOLAMBDA = "ecolambda"
    ECOSTER = "ecoster"
    PANEL = "panel"


@unique
class ProductModel(StrEnum):
    """Known ecoMAX models."""

    ECOMAX_350P2_ZF = "ecoMAX 350P2-ZF"
    ECOMAX_850I = "ecoMAX 850i"
    ECOMAX_850P2_C = "ecoMAX 850P2-C"
    ECOMAXX_800R3 = "ecoMAXX 800R3"
    ECOMAX_860D3_HB = "ecoMAX 860D3-HB"
    ECOMAX_860P3_O = "ecoMAX 860P3-O"
    ECOMAX_860P6_O = "ecoMAX 860P6-O"
    ECOMAX_860P3_S_LITE = "ecoMAX 860P3-S LITE"
    ECOMAX_920P1_O = "ecoMAX 920P1-O"
