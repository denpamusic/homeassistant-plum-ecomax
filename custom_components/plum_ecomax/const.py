"""Constants for the Plum ecoMAX integration."""

import re
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

ECOMAX: Final = "ecomax"

ATTR_VALUE: Final = "value"
ATTR_CODE: Final = "code"
ATTR_FROM: Final = "from"
ATTR_TO: Final = "to"

CONNECTION_TYPE_TCP: Final = "TCP"
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPES: Final = (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL)

DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_PORT: Final = 8899
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"

FLOW_KGH: Final = "kg/h"
CALORIFIC_KWH_KG: Final = "kWh/kg"

ECOMAX_ALERT_EVENT: Final = "alert"

ECOMAX_P = re.compile(r"(em|ecomax)\s{0,}[0-9]{3,}p", re.IGNORECASE)
ECOMAX_I = re.compile(r"(em|ecomax)\s{0,}[0-9]{3,}i", re.IGNORECASE)
