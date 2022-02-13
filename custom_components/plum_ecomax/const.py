"""Constants for the Plum ecoMAX integration."""

from typing import Final

from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_OFF,
    STATE_PERFORMANCE,
)

DOMAIN = "plum_ecomax"

DEFAULT_PORT: Final = 8899
DEFAULT_INTERVAL: Final = 10
MIN_INTERVAL: Final = 10
MAX_INTERVAL: Final = 60
CONNECTION_CHECK_TRIES: Final = 5

FLOW_KGH: Final = "kg/h"

WATER_HEATER_MODES: Final = (STATE_OFF, STATE_PERFORMANCE, STATE_ECO)
