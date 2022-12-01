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
CONF_PRODUCT_TYPE: Final = "product_type"
CONF_SOFTWARE: Final = "software"
CONF_CAPABILITIES: Final = "capabilities"

MANUFACTURER: Final = "Plum Sp. z o.o."
ECOMAX: Final = "ecomax"

ATTR_VALUE: Final = "value"
ATTR_CODE: Final = "code"
ATTR_FROM: Final = "from"
ATTR_TO: Final = "to"
ATTR_MIXERS: Final = "mixers"
ATTR_SCHEDULES: Final = "schedules"
ATTR_PASSWORD: Final = "password"
ATTR_PRODUCT: Final = "product"
ATTR_FUEL_BURNED: Final = "fuel_burned"
ATTR_WATER_HEATER: Final = "water_heater"
ATTR_ECOMAX_CONTROL: Final = "ecomax_control"

CONNECTION_TYPE_TCP: Final = "TCP"
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPES: Final = (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL)

DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_PORT: Final = 8899
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"

FLOW_KGH: Final = "kg/h"
CALORIFIC_KWH_KG: Final = "kWh/kg"

ECOMAX_ALERT_EVENT: Final = "plum_ecomax_event"
