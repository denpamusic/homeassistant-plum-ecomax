"""Platform for binary sensor integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .entity import EcomaxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform.

    Keyword arguments:
        hass -- instance of Home Assistant core
        config_entry -- instance of config entry
        async_add_entities -- callback to add entities to hass
    """
    connection = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        EcomaxBinarySensor(connection, "heating_pump", "Heating Pump State"),
        EcomaxBinarySensor(connection, "water_heater_pump", "Water Heater Pump State"),
        EcomaxBinarySensor(connection, "fan", "Fan State"),
        EcomaxBinarySensor(connection, "lighter", "Lighter State"),
    ]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Binary sensor representation."""

    async def async_update_state(self):
        """Update entity state."""
        self._state = self.get_attribute(self._id)
        self.async_write_ha_state()

    @property
    def state(self):
        """Return the state of the sensor."""
        return STATE_ON if self._state else STATE_OFF
