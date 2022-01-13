"""Platform for sensor integration."""
from __future__ import annotations

import logging

from pyplumio.devices import EcoMAX

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .connection import EcomaxConnection
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    switches = [EcomaxSwitch("boiler_control", "Regulator State")]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(switches, async_add_entities)


class EcomaxSwitch(SwitchEntity):
    def __init__(self, id: str, name: str):
        self._id = id
        self._name = name
        self._state = False
        self._ecomax = None

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        if self._ecomax is not None:
            setattr(self._ecomax, self._id, 1)
            self._state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        if self._ecomax is not None:
            setattr(self._ecomax, self._id, 0)
            self._state = False
            self.async_write_ha_state()

    async def update_sensor(self, ecomax: EcoMAX):
        """Set up ecoMAX device instance."""
        if self._ecomax is None:
            self._ecomax = ecomax
            self.async_write_ha_state()

    def set_connection(self, connection: EcomaxConnection):
        """Set up ecoMAX connection instance."""
        self._connection = connection

    @property
    def is_on(self) -> bool:
        """Return switch state."""
        if self._ecomax is not None:
            return bool(int(getattr(self._ecomax, self._id)))

        return False

    @property
    def unique_id(self) -> str:
        """Return unique id of switch."""
        return f"{self._connection.name}{self._id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._connection.name} {self._name}"

    @property
    def should_poll(self):
        """Sensor shouldn't use polling."""
        return False
