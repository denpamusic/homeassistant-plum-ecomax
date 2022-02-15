"""Platform for number integration."""
from __future__ import annotations

from typing import Optional

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
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
    """Set up the number platform.

    Keyword arguments:
        hass -- instance of Home Assistant core
        config_entry -- instance of config entry
        async_add_entities -- callback to add entities to hass
    """
    connection = hass.data[DOMAIN][config_entry.entry_id]
    numbers = [
        EcomaxNumberTemperature(connection, "heating_set_temp", "Heating Temperature"),
        EcomaxNumberTemperature(
            connection, "heating_temp_grate", "Grate Mode Temperature"
        ),
        EcomaxNumberTemperature(
            connection, "min_heating_set_temp", "Minimum Heating Temperature"
        ),
        EcomaxNumberTemperature(
            connection, "max_heating_set_temp", "Maximum Heating Temperature"
        ),
        EcomaxNumberPercent(
            connection, "min_fuzzy_logic_power", "Fuzzy Logic Minimum Power"
        ),
        EcomaxNumberPercent(
            connection, "max_fuzzy_logic_power", "Fuzzy Logic Maximum Power"
        ),
    ]
    await connection.add_entities(numbers, async_add_entities)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Ecomax number entity representation."""

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
    def value(self) -> Optional[float]:
        attr = self.get_attribute(self._id)
        return None if attr is None else attr.value

    @property
    def min_value(self) -> float:
        attr = self.get_attribute(self._id)
        return 0 if attr is None else attr.min_

    @property
    def max_value(self) -> float:
        attr = self.get_attribute(self._id)
        return 0 if attr is None else attr.max_


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
