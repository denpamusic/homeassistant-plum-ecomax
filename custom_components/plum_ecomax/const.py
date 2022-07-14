"""Constants for the Plum ecoMAX integration."""

from typing import Final

DOMAIN = "plum_ecomax"

CONF_CONNECTION_TYPE: Final = "connection_type"
CONF_TITLE: Final = "title"
CONF_DEVICE: Final = "device"
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_UID: Final = "uid"
CONF_MODEL: Final = "model"
CONF_SOFTWARE: Final = "software"
CONF_CAPABILITIES: Final = "capabilities"

CONNECTION_TYPE_TCP: Final = "TCP"
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPES: Final = (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL)

DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_PORT: Final = 8899
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"

FLOW_KGH: Final = "kg/h"
CALORIFIC_KWH_KG: Final = "kWh/kg"

DEVICE_CLASS_METER: Final = "plum_ecomax__meter"
DEVICE_CLASS_STATE: Final = "plum_ecomax__mode"

SERVICE_RESET_METER: Final = "reset_meter"
SERVICE_CALIBRATE_METER: Final = "calibrate_meter"

ATTR_VALUE: Final = "value"
