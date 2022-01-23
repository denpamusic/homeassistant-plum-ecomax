"""Constants for the Plum ecoMAX integration."""

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_PERFORMANCE,
)

DOMAIN = "plum_ecomax"

DEFAULT_PORT = 8899
DEFAULT_INTERVAL = 10
MIN_INTERVAL = 10
MAX_INTERVAL = 60
CONNECTION_CHECK_TRIES = 5

FLOW_KGH = "kg/h"

WATER_HEATER_MODES = (STATE_OFF, STATE_PERFORMANCE, STATE_ECO)
