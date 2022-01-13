"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import EcoMAX

from .connection import EcomaxConnection
from .const import DOMAIN
from .entity import EcomaxEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    switches = [
        EcomaxSwitch("boiler_control", "Regulator State Switch"),
        EcomaxSwitch("program_control_co", "Weather Control Switch"),
        EcomaxSwitch("cwu_work_mode", "Water Heater Pump Switch", off=0, on=2),
        EcomaxSwitch("cwu_disinfection", "Water Heater Disinfection Switch"),
    ]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(switches, async_add_entities)


class EcomaxSwitch(EcomaxEntity, SwitchEntity):
    def __init__(self, id_: str, name: str, off: int = 0, on: int = 1):
        super().__init__(id_=id_, name=name)
        self._ecomax = None
        self._on = on
        self._off = off

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        if self._ecomax is not None:
            self._ecomax.__setattr__(self._id, self._on)
            self._state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        if self._ecomax is not None:
            self._ecomax.__setattr__(self._id, self._off)
            self._state = False
            self.async_write_ha_state()

    async def update_sensor(self, ecomax: EcoMAX):
        """Set up ecoMAX device instance."""
        if self._ecomax is None:
            self._ecomax = ecomax

        state = getattr(self._ecomax, self._id).value == self._on
        if state != self._state:
            self._state = state
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return switch state."""
        return self._state
