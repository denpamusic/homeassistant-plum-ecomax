"""Constants for the Plum ecoMAX integration."""

from typing import Final

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_PERFORMANCE,
)

DOMAIN = "plum_ecomax"

MANUFACTURER: Final = "Plum"
CONF_CONNECTION_TYPE: Final = "connection_type"
CONF_DEVICE: Final = "device"
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_UID: Final = "uid"
CONF_MODEL: Final = "model"
CONF_SW_VERSION: Final = "sw_version"
CONNECTION_CHECK_TRIES: Final = 5
CONNECTION_TYPE_TCP: Final = "TCP"
CONNECTION_TYPE_SERIAL: Final = "Serial"
CONNECTION_TYPES: Final = (CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL)
DEFAULT_CONNECTION_TYPE: Final = CONNECTION_TYPE_TCP
DEFAULT_PORT: Final = 8899
DEFAULT_UPDATE_INTERVAL: Final = 10
DEFAULT_DEVICE: Final = "/dev/ttyUSB0"
DEFAULT_HOST: Final = "192.168.100.1"
MIN_UPDATE_INTERVAL: Final = 10

FLOW_KGH: Final = "kg/h"

WATER_HEATER_MODES: Final = (STATE_OFF, STATE_PERFORMANCE, STATE_ECO)
