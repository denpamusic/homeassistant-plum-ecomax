"""Constants for the Plum ecoMAX integration."""

from enum import StrEnum, unique
from typing import Final

DOMAIN = "plum_ecomax"

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
DEFAULT_TOLERANCE: Final = 1

# Events.
EVENT_PLUM_ECOMAX_ALERT: Final = "plum_ecomax_alert"


@unique
class DeviceType(StrEnum):
    """Known devices, represented by PyPlumIO's Device class."""

    ECOMAX = "ecomax"
    MIXER = "mixer"
    THERMOSTAT = "thermostat"


VIRTUAL_DEVICES: Final = (DeviceType.MIXER, DeviceType.THERMOSTAT)


@unique
class ModuleType(StrEnum):
    """Known ecoMAX modules."""

    A = "module_a"
    B = "module_b"
    C = "module_c"
    ECOLAMBDA = "ecolambda"
    ECOSTER = "ecoster"
    PANEL = "panel"
