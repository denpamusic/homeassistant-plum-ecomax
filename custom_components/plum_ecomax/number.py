"""Platform for number integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    EntityDescription,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.helpers.parameter import Parameter

from .connection import EcomaxConnection
from .const import DOMAIN
from .entity import EcomaxEntity


@dataclass
class EcomaxNumberEntityDescription(NumberEntityDescription):
    """Describes ecoMAX number entity."""


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        name="Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate Mode Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        name="Minimum Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        name="Maximum Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        name="Fuzzy Logic Minimum Power",
        native_unit_of_measurement=PERCENTAGE,
        step=1,
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        name="Fuzzy Logic Maximum Power",
        native_unit_of_measurement=PERCENTAGE,
        step=1,
    ),
)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Represents ecoMAX number platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_native_value: float | None
    _attr_min_value: float | None
    _attr_max_value: float | None

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxNumberEntityDescription
    ):
        self._connection = connection
        self.entity_description = description
        self._attr_native_value = None
        self._attr_min_value = None
        self._attr_max_value = None

    async def async_set_native_value(self, value: float) -> None:
        """Update current value."""
        await self.device.set_value(self.entity_description.key, value)
        self._attr_native_value = int(value)
        self.async_write_ha_state()

    async def async_update(self, value: Parameter) -> None:
        """Update entity state."""
        self._attr_native_value = value.value
        self._attr_min_value = value.min_value
        self._attr_max_value = value.max_value
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the number platform."""
    connection = hass.data[DOMAIN][config_entry.entry_id]
    return async_add_entities(
        [EcomaxNumber(connection, description) for description in NUMBER_TYPES], False
    )
