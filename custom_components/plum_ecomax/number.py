"""Platform for number integration."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.devices import EcoMAX

from .const import DOMAIN
from .entity import EcomaxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform.

    Keyword arguments:
        hass -- instance of Home Assistant core
        config_entry -- instance of config entry
        async_add_entities -- callback to add entities to hass
    """
    sensors = [
        EcomaxNumberTemperature("heating_set_temp", "Heating Temperature"),
        EcomaxNumberTemperature("heating_temp_grate", "Grate Mode Temperature"),
        EcomaxNumberTemperature("min_heating_set_temp", "Minimum Heating Temperature"),
        EcomaxNumberTemperature("max_heating_set_temp", "Maximum Heating Temperature"),
        EcomaxNumberPercent("min_fuzzy_logic_power", "Fuzzy Logic Minimum Power"),
        EcomaxNumberPercent("max_fuzzy_logic_power", "Fuzzy Logic Maximum Power"),
    ]

    connection = hass.data[DOMAIN][config_entry.entry_id]
    await connection.add_entities(sensors, async_add_entities)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """ecoMAX number entity representation."""

    async def async_update_state(self) -> None:
        """Update entity state."""
        self.async_write_ha_state()

    async def async_set_value(self, value: float) -> None:
        """Update the current value.

        Keyword arguments:
            value -- new number value
        """
        self.set_attribute(self._id, int(value))
        self.async_write_ha_state()

    @property
    def value(self) -> float:
        attr = self.get_attribute(self._id)
        if attr is not None:
            return attr.value

        return 0

    @property
    def min_value(self) -> float:
        attr = self.get_attribute(self._id)
        if attr is not None:
            return attr.min_

        return 0

    @property
    def max_value(self) -> float:
        attr = self.get_attribute(self._id)
        if attr is not None:
            return attr.max_

        return 0


class EcomaxNumberTemperature(EcomaxNumber):
    """Setup temperature number."""

    @property
    def unit_of_measurement(self) -> str:
        return TEMP_CELSIUS


class EcomaxNumberPercent(EcomaxNumber):
    """Setup percent number."""

    @property
    def unit_of_measurement(self) -> str:
        return PERCENTAGE
