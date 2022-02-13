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
    sensors = [
        EcomaxBinarySensor("heating_pump", "Heating Pump State"),
        EcomaxBinarySensor("water_heater_pump", "Water Heater Pump State"),
        EcomaxBinarySensor("fan", "Fan State"),
        EcomaxBinarySensor("lighter", "Lighter State"),
    ]
    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxBinarySensor(EcomaxEntity, BinarySensorEntity):
    """Binary sensor representation."""

    async def async_update_state(self):
        """Update entity state."""
        state = self.get_attribute(self._id)
        if state is not None:
            state = STATE_ON if state else STATE_OFF
            if self._state != state:
                self._state = state
                self.async_write_ha_state()

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
