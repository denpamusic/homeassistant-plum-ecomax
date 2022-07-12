"""Platform for number integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    EntityDescription,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from pyplumio.helpers.filters import on_change
from pyplumio.helpers.parameter import Parameter

from .connection import EcomaxConnection
from .const import CALORIFIC_KWH_KG, DOMAIN
from .entity import EcomaxEntity


@dataclass
class EcomaxNumberEntityAdditionalKeys:
    """Additional keys for ecoMAX number entity description."""

    value_get_fn: Callable[[Any], Any]
    value_set_fn: Callable[[Any], Any]


@dataclass
class EcomaxNumberEntityDescription(
    NumberEntityDescription, EcomaxNumberEntityAdditionalKeys
):
    """Describes ecoMAX number entity."""

    filter_fn: Callable[[Any], Any] = on_change
    mode: NumberMode = NumberMode.AUTO


NUMBER_TYPES: tuple[EcomaxNumberEntityDescription, ...] = (
    EcomaxNumberEntityDescription(
        key="heating_target_temp",
        name="Heating Target Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="heating_temp_grate",
        name="Grate Mode Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="min_heating_target_temp",
        name="Minimum Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_heating_target_temp",
        name="Maximum Heating Temperature",
        native_unit_of_measurement=TEMP_CELSIUS,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="min_fuzzy_logic_power",
        name="Fuzzy Logic Minimum Power",
        native_unit_of_measurement=PERCENTAGE,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="max_fuzzy_logic_power",
        name="Fuzzy Logic Maximum Power",
        native_unit_of_measurement=PERCENTAGE,
        native_step=1,
        value_get_fn=lambda x: x,
        value_set_fn=lambda x: x,
    ),
    EcomaxNumberEntityDescription(
        key="fuel_calorific_value_kwh_kg",
        name="Fuel Calorific Value",
        native_unit_of_measurement=CALORIFIC_KWH_KG,
        native_step=0.1,
        value_get_fn=lambda x: x / 10,
        value_set_fn=lambda x: x * 10,
        mode=NumberMode.BOX,
    ),
)


class EcomaxNumber(EcomaxEntity, NumberEntity):
    """Represents ecoMAX number platform."""

    _connection: EcomaxConnection
    entity_description: EntityDescription
    _attr_native_value: float | None
    _attr_native_min_value: float | None
    _attr_native_max_value: float | None
    _attr_mode: NumberMode = NumberMode.AUTO

    def __init__(
        self, connection: EcomaxConnection, description: EcomaxNumberEntityDescription
    ):
        self._connection = connection
        self.entity_description = description
        self._attr_native_value = None
        self._attr_native_min_value = None
        self._attr_native_max_value = None
        self._attr_mode = description.mode

    async def async_set_native_value(self, value: float) -> None:
        """Update current value."""
        await self.device.set_value(
            self.entity_description.key, self.entity_description.value_set_fn(value)
        )
        self._attr_native_value = value
        self.async_write_ha_state()

    async def async_update(self, value: Parameter) -> None:
        """Update entity state."""
        self._attr_native_value = self.entity_description.value_get_fn(value.value)
        self._attr_native_min_value = self.entity_description.value_get_fn(
            value.min_value
        )
        self._attr_native_max_value = self.entity_description.value_get_fn(
            value.max_value
        )
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
