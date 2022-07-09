"""Platform for number integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .entity import EcomaxEntity


@dataclass
class EcomaxNumberEntityDescription(NumberEntityDescription):
    """Describes ecoMAX number entity."""


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        name="Heating Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate Mode Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        name="Minimum Heating Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        name="Maximum Heating Temperature",
        unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        name="Fuzzy Logic Minimum Power",
        unit_of_measurement=PERCENTAGE,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        name="Fuzzy Logic Maximum Power",
        unit_of_measurement=PERCENTAGE,
        step=1,
    ),
)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Representation of ecoMAX number."""

    def __init__(self, connection, description: EcomaxNumberEntityDescription):
        self._connection = connection
        self.entity_description = description
        self._attr_native_value: float | None = None
        self._attr_min_value = None
        self._attr_max_value = None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value.

        Keyword arguments:
            value -- new number value
        """
        setattr(self._connection.ecomax, self.entity_description.key, int(value))
        self._attr_native_value = int(value)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update entity state."""
        parameter = getattr(self._connection.ecomax, self.entity_description.key, None)

        if parameter is None:
            self._attr_native_value = None
            self._attr_min_value = None
            self._attr_max_value = None
        else:
            self._attr_native_value = parameter.value
            self._attr_min_value = parameter.min_value
            self._attr_max_value = parameter.max_value

        self.async_write_ha_state()


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
    async_add_entities(
        [EcomaxNumber(connection, description) for description in NUMBER_TYPES], False
    )
