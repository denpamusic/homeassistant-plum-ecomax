"""Platform for binary sensor integration."""
from __future__ import annotations

import logging

from pyplumio.devices import EcoMAX

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import STATE_OFF, STATE_ON
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
    sensors = [
        EcomaxBinarySensor("co_pump", "CO Pump State"),
        EcomaxBinarySensor("cwu_pump", "CWU Pump State"),
        EcomaxBinarySensor("fan", "Fan State"),
        EcomaxBinarySensor("lighter", "Lighter State"),
    ]
    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxBinarySensor(BinarySensorEntity):
    """Binary sensor representation."""

    def __init__(self, id: str, name: str):
        self._state = None
        self._id = id
        self._name = name

    async def update_sensor(self, ecomax: EcoMAX):
        """Update sensor state. Called by connection instance."""
        attr = getattr(ecomax, self._id)
        if attr != self._state:
            self._state = STATE_ON if attr else STATE_OFF
            self.async_write_ha_state()

    def set_connection(self, connection: EcomaxConnection):
        """Set ecoMAX connection instance."""
        self._connection = connection

    @property
    def unique_id(self) -> str:
        return f"{self._connection.name}{self._id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._connection.name} {self._name}"

    @property
    def should_poll(self):
        """Sensor shouldn't use polling."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
